# wechatLogAutoDB
a local extranal tool for chatlog
本工具是Chatlog的应用扩展插件平台，当您使用了Chatlog，可以依靠wechatLogAutoDB获得本地excel文件及web查询服务。
本工具的数据来自于Chatlog发布的API（聊天记录、联系人等），存储于对应目录的xlsx文件中，没有其他远程存储，请放心使用。

##安装使用
使用前，确保安装了python3.8+及其依赖组件requests、pandas、schedule、flask，如果没有请自行使用：
```
pip install [组件名称]
```
然后运行本py工具即可：
```
python chatlogAI_saveWechat.py
```
本工具将发布一个端口为5000的web应用，打开：http://localhost:5000或http://yourip:5000 即可访问。

# Chatlog

![chatlog](https://socialify.git.ci/sjzar/chatlog/image?font=Rokkitt&forks=1&issues=1&name=1&pattern=Diagonal+Stripes&stargazers=1&theme=Auto)

_聊天记录工具，帮助大家轻松使用自己的聊天数据_

详细查看：https://github.com/sjzar/chatlog
