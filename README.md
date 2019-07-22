# yuanshen-trend
Python 3.7.x based micro-service designed for tracking Genshin Impact on TapTap.

基于Python 3.7.x的微服务，用于追踪TapTap论坛@原神舆论趋势(热词)。


## 特点 / Highlights

- 近乎实时追踪 / Almost real-time tracking
- 对回复较多的帖子采取增量更新 / Incremental updates for those topics which have lots of comments
- 易于扩展其他数据源 / Easy to expand for other data source
- 可轻松更换数据库驱动(默认SQLite) / Easy to replace DB driver. (Default: SQLite)
- 使用HTTP API进行交互 / Interact using HTTP API
- 架构灵活，便于扩展新功能 / Flexible architect and easy for customization

> 虽然写的是追踪原神，实际上，**该程序可以追踪TapTap上任意一款游戏的论坛舆论趋势**


 ## 依赖 / Requirements
 
* Python >= `3.7.0`
* beautifulsoup4 >= `3.8.0`
* jieba >= `0.39`
* lxml >= `4.3.4`


## 例子 / Examples

**1. 假设你需要追踪原神的TapTap舆论情况 / Assuming you want to track Genshin Impact on taptap**
  - 先确认原神在TapTap的URL / First, locate the URL of Genshin on taptap
    ```
    https://www.taptap.com/app/168332
    ```

**2. 运行程序 / Run program**
  ```
  python3 link_start.py
  ```
  
**3. 调用HTTP API / Call HTTP API**
  ```
  GET http://127.0.0.1:1571/?url=https://www.taptap.com/app/168332&action=data&day=7
  ```
  > 收集对应游戏7天内的帖子数据 / This will collect community posts data of corresponding app within 7 days

**4. 执行增量更新 / Perform incremental updates**
  ```
  GET http://127.0.0.1:1571/?url=https://www.taptap.com/app/168332&action=update
  ```
  > 更新所有最近被回复过的帖子 / This will update those topics which are commented recently
  
  > 你应该定期执行该任务(例如crontab)以保持追踪 / You should perfrom this regularly(eg. crontab) to keep tracking

**5. 获得近期热词 / Extract recent top-words**
  ```
  http://127.0.0.1:1571/?url=https://www.taptap.com/app/168332&action=countword&word=100&updated_since=timestamp_since&updated_till=timestamp_till
  ```
  > 需要注意的是程序并不会校验请求参数 / Be cautious that you may encounter an Exception causing program will NOT validate the request param
  
  > 你需要注意请求格式正确 / You should double-check the param before requesting

  ### 注意事项 / Notice
  因为TapTap论坛设计的问题，楼中楼回复不会顶帖，所以建议定期执行以下的任务，保持楼中楼回复被正确记录。

  Due to some flaw of TapTap community, you are advised to perform the task below regularly. In order to keep recording comments of comments correctly into database.
  ```
  GET http://127.0.0.1:1571/?url=https://www.taptap.com/app/168332&action=data
  ```


## API

  | Param | Type | Necessary | Note |
  |:--|:--:|:--|:--|
  | url | string | YES | Tell the program what kind of sub-class should be instantiated. |
  | action | string\[data\|update\|json\|countword\|labels\] | YES | Specify the `action` program should do. |
  | updated_since | timestamp | NO | Using `updated_time` to specify the time START when quering for data. |
  | updated_till | timestamp | NO | Using `updated_time` to specify the time END when quering for data. |
  | created_since | timestamp | NO | Similar to above but using `created_time`. |
  | created_till | timestamp | NO | Similar to above but using `created_time`. |
  | commented_since | timestamp | NO | Similar to above but using `commented_time`. |
  | commented_till | timestamp | NO | Similar to above but using `commented_time`. |
  | day | integer | NO | Used to indicate how many days of data should be collected when doing `data` `action`. |
  | tid | integer | NO | Used to indicate which post should be selected when doing `json` `action`. |
  | elite | integer\[0\|1\] | NO | `elite=1` will apply a WHERE statement `AND elite = 1` indicating only return elite topic and its comments when quering for data. And vice verse.  |
  | official | integer\[0\|1\] | NO | `official=1` will apply a WHERE statement `AND official = 1` indicating only return official topic and its comments when quering for data. And vice verse.  |
  | label | single integer or comma-splitted integers | NO | Act as a filter to only return data with specified label(s). You can get available labels by doing `labels` `action`. |


## TODO
  - 多线程获取数据 / Muti-threads for data fetching


## Licence
[MIT license](https://opensource.org/licenses/MIT).
