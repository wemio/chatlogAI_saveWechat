#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成脚本：定时拉取 API 数据保存到 Excel，并提供 Flask HTTP 服务分页/搜索展示（HTML 页面）。

新增：
- 当 nickName 为空时，调用 联系人 接口获取 remark 或 nickName，并更新 Excel。
- sessions 页面查询按钮后增加“首页”链接。
- 禁用环境代理，确保本地接口调用不走代理。
"""

import os
import json
import time
import math
import threading
from urllib.parse import quote_plus

import requests
import pandas as pd
import schedule
from flask import Flask, request, render_template_string

# —— 禁用环境代理 —— #
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(var, None)

# —— 全局配置 —— #
API_URL        = 'http://localhost:5030/api/v1/session?format=json'
CHATROOM_API   = 'http://localhost:5030/api/v1/chatroom?keyword={}&format=json'
CONTACT_API    = 'http://localhost:5030/api/v1/contact?keyword={}&format=json'

OUTPUT_DIR     = r'D:\AI\chatlog_0.0.15_windows_amd64\app\wechatData2025'
EXCEL_FILE     = os.path.join(OUTPUT_DIR, 'session_data.xlsx')
STATE_FILE     = os.path.join(OUTPUT_DIR, 'last_state.json')
COLUMNS        = ['userName', 'nOrder', 'nickName', 'content', 'nTime']

app = Flask(__name__)
chatroom_cache = {}
contact_cache  = {}

# —— 定时拉取 & Excel 更新 —— #
def load_last_order():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('last_nOrder', 0)
    return 0

def save_last_order(n_order: int):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'last_nOrder': n_order}, f, ensure_ascii=False, indent=2)

def get_contact_name(userName: str) -> str:
    """调用联系人接口，优先取 remark，否则 nickName。"""
    if userName in contact_cache:
        return contact_cache[userName]
    try:
        url = CONTACT_API.format(quote_plus(userName))
        r = requests.get(url, timeout=5, proxies={'http': None, 'https': None})
        r.raise_for_status()
        items = r.json().get('items', [])
        if items:
            it = items[0]
            name = it.get('remark') or it.get('nickName') or userName
            contact_cache[userName] = name
            return name
    except Exception:
        pass
    contact_cache[userName] = userName
    return userName

def get_chatroom_name(userName: str) -> str:
    """调用群聊接口取 nickName/name。"""
    if userName in chatroom_cache:
        return chatroom_cache[userName]
    try:
        url = CHATROOM_API.format(quote_plus(userName))
        r = requests.get(url, timeout=5, proxies={'http': None, 'https': None})
        r.raise_for_status()
        items = r.json().get('items', [])
        if items:
            it = items[0]
            name = it.get('nickName') or it.get('name') or userName
            chatroom_cache[userName] = name
            return name
    except Exception:
        pass
    chatroom_cache[userName] = userName
    return userName

def fetch_and_append():
    last_order = load_last_order()
    try:
        resp = requests.get(API_URL, timeout=10, proxies={'http': None, 'https': None})
        resp.raise_for_status()
        items = resp.json().get('items', [])
        df = pd.DataFrame(items)
        if df.empty:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - items 为空")
            return

        df['nOrder'] = df['nOrder'].astype(int)
        new_df = df[df['nOrder'] > last_order].sort_values('nOrder')
        if new_df.empty:
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 无新数据")
            return

        # 打印新增
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 新增数据：")
        print(new_df.to_string(index=False, columns=COLUMNS))

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if os.path.exists(EXCEL_FILE):
            old_df = pd.read_excel(EXCEL_FILE, dtype={'nOrder': int})
            combined = pd.concat([old_df, new_df], ignore_index=True)
        else:
            combined = new_df.copy()

        combined = combined[COLUMNS]

        # 填充空 nickName
        for idx, row in combined.iterrows():
            if not row['nickName'] or pd.isna(row['nickName']) or not str(row['nickName']).strip():
                combined.at[idx, 'nickName'] = get_contact_name(row['userName'])
            if '@chatroom' in row['userName']:
                combined.at[idx, 'nickName'] = get_chatroom_name(row['userName'])

        combined.to_excel(EXCEL_FILE, index=False)

        max_order = new_df['nOrder'].max()
        save_last_order(int(max_order))
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 已追加 {len(new_df)} 条，新 max nOrder={max_order}")

    except Exception as e:
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 拉取异常：{e}")

def scheduler_thread():
    fetch_and_append()
    schedule.every(3).minutes.do(fetch_and_append)
    while True:
        schedule.run_pending()
        time.sleep(1)

# —— 数据加载与展示 —— #
def load_data() -> pd.DataFrame:
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_excel(EXCEL_FILE, dtype=str)
    df['nTime'] = pd.to_datetime(df['nTime'])
    return df.sort_values('nTime',ascending=False)

@app.route('/sessions')
def sessions():
    page     = max(1, int(request.args.get('page', 1)))
    per_page = max(1, int(request.args.get('per_page', 20)))
    keyword  = request.args.get('keyword', '').strip()

    df = load_data()
    if keyword:
        mask = (
            df['userName'].str.contains(keyword, na=False) |
            df['nickName'].str.contains(keyword, na=False) |
            df['content'].str.contains(keyword, na=False)
        )
        df = df[mask]

    total = len(df)
    pages = math.ceil(total / per_page)
    start = (page-1)*per_page
    end   = start + per_page
    page_df = df.iloc[start:end].copy()

    rows = list(page_df.itertuples(index=False, name='Row'))

    html = render_template_string("""
<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>会话记录</title>
<style>
 table{width:100%;border-collapse:collapse;}
 th,td{padding:8px;border:1px solid #ccc;text-align:left;}
 form{margin-bottom:1em;}
 .pager a{margin:0 5px;text-decoration:none;}
</style>
</head>
<body>
  <h2>会话记录</h2>
  <form method="get">
    关键词：<input name="keyword" value="{{keyword}}">
    每页：<input name="per_page" size="3" value="{{per_page}}">
    <button type="submit">查询</button>&nbsp;&nbsp;<a href="?">首页</a>
  </form>
  <table>
    <thead><tr><th>时间</th><th>用户</th><th>昵称</th><th>内容</th></tr></thead>
    <tbody>
    {% for r in rows %}
      <tr>
        <td>{{ r.nTime }}</td>
        <td>{{ r.userName }}</td>
        <td>{{ r.nickName }}</td>
        <td>{{ r.content }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <div class="pager">
    共 {{total}} 条，页 {{page}}/{{pages}}
    {% if page>1 %}
      <a href="?page=1&per_page={{per_page}}&keyword={{keyword}}">首页</a>
      <a href="?page={{page-1}}&per_page={{per_page}}&keyword={{keyword}}">上一页</a>
    {% endif %}
    {% if page<pages %}
      <a href="?page={{page+1}}&per_page={{per_page}}&keyword={{keyword}}">下一页</a>
      <a href="?page={{pages}}&per_page={{per_page}}&keyword={{keyword}}">末页</a>
    {% endif %}
  </div>
</body>
</html>
""",
        rows=rows, page=page, pages=pages,
        per_page=per_page, keyword=keyword, total=total
    )
    return html

# —— 启动入口 —— #
if __name__ == '__main__':
    t = threading.Thread(target=scheduler_thread, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000, debug=False)
