import json
from sourcelib.BaseSource import BaseSource
from sourcelib.basiclib import *
from urllib.parse import quote
import jieba
import jieba.analyse
import re
from collections import Counter
# from wordcloud import WordCloud
# import matplotlib.pylab as plt
# import matplotlib.font_manager as pltf
# from numpy import arange


class SourceTapTap(BaseSource):

    # API每次请求的列表大小
    pageLimit = 10

    # debug FLAG
    debug = False

    def __init__(self, parsed_url, action):
        super().__init__(parsed_url, action)
        self.appID = self.__getAppID()
        self.labelIDs = self.__getLabel()
        self.__touchDBTable()
        # should be triggered at LAST
        self.do_action()

    def cookie_file_name(self):
        return None

    def sqlite_file_name(self):
        path = self.parsedURL.path
        res = re.search(r'/app/([0-9]+)/?', path)
        if res is not None:
            return 'data/' + self.__class__.__name__ + '/data-' + res[1] + '.db'
        return super().sqlite_file_name()

    def __getLabel(self):
        lb = self.queryDict.get('label')
        if lb is not None:
            return lb.split(',')
        return None

    def __getLabelStr(self):
        if isinstance(self.labelIDs, list):
            strArr = [self.__labelMap(int(v)) for v in self.labelIDs]
            return ','.join(strArr)
        elif isinstance(self.labelIDs, int):
            return self.__labelMap(self.labelIDs)
        return '所有'

    def __labelMap(self, lid):
        sql = 'SELECT label_id, label_name FROM labels'
        res = self.DBExecute(sql).fetchall()
        labelDict = {i[0]: i[1] for i in res}

        if labelDict.get(lid) is not None:
            return labelDict[lid]
        return str(lid)

    def __getLabelTuples(self):
        api = 'https://api.taptapdada.com/group/v1/detail'
        params = {
            'show_app': 0
        }
        js = self.__getJSONResp(api, params)
        terms = js['data']['group']['terms']
        labels = []
        for i in terms:
            if i['management_params'].get('type') is not None and i['management_params'].get('type') == 'all':
                labels.append((0, i['label']))
            elif i['management_params'].get('group_label_id') is not None:
                labels.append((i['index'], i['label']))

        return labels

    def __collectLabelData(self):
        labels = self.__getLabelTuples()
        self.debug_output('[labels] ' + str(labels))
        # 写入数据库
        self.DBExecuteMany('REPLACE INTO labels VALUES (?, ?)', labels)

    def __getAppID(self):
        path = self.parsedURL.path
        res = re.search(r'/app/([0-9]+)/?', path)
        if res is not None:
            return int(res[1])
        # 默认原神
        return 168332

    def __createDBTable(self, table, structure):
        c = self.DBExecute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{}';".format(table))
        c = c.fetchone()
        if c[0] == 0:
            self.debug_output('[SQLite] data table <{}> not exist! creating a new one...'.format(table))
            self.DBExecute(structure)
            self.debug_output('[SQLite] data table <{}> created!'.format(table))
        else:
            self.debug_output('[SQLite] data table <{}> already created!'.format(table))

    def __touchDBTable(self):
        # table definition
        tb = {
            'posts': """CREATE TABLE posts (
                        topic_id  INTEGER NOT NULL DEFAULT 0,
                        post_id   INTEGER NOT NULL DEFAULT 0,
                        author_id INTEGER,
                        title     TEXT NOT NULL DEFAULT '',
                        content   TEXT,
                        label_id  INTEGER NOT NULL DEFAULT 0,
                        elite     INTEGER NOT NULL DEFAULT 0,
                        official  INTEGER NOT NULL DEFAULT 0,
                        created_time   INTEGER,
                        updated_time   INTEGER,
                        commented_time INTEGER NOT NULL DEFAULT 0,
                        comments  INTEGER NOT NULL DEFAULT 0,
                        ups       INTEGER NOT NULL DEFAULT 0,
                        downs     INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY ( topic_id, post_id )
            );""",
            'labels': """CREATE TABLE labels (
                        label_id  INTEGER NOT NULL DEFAULT 0,
                        label_name  TEXT NOT NULL,
                        PRIMARY KEY ( label_id )
            );"""
        }
        for (table, structure) in tb.items():
            self.__createDBTable(table, structure)

    def __buildInsertTuple(self, item):
        if isinstance(item, dict):
            return (
                item['topic_id'], item['post_id'], item['author_id'],
                item['title'], item['content'],
                item['label_id'], item['elite'], item['official'],
                item['created_time'], item['updated_time'], item['commented_time'],
                item['comments'], item['ups'], item['downs']
            )
        tuples = []
        for i in item:
            tuples.append(self.__buildInsertTuple(i))
        return tuples

    def __getCommonQuery(self):
        dt = {
            'app_id': self.appID,
            'X-UA': 'V=1&PN=TapTap&VN_CODE=557&LOC=CN&LANG=zh_CN&CH=default&UID=f7ad0c05-a231-48b8-b5a8-852850de52b0',
        }
        return dt

    def __getFinalQuery(self, param):
        dt = self.__getCommonQuery()
        for k, v in param.items():
            dt[k] = v
        tp = []
        for k, v in dt.items():
            if v is not None:
                tp.append(quote(str(k).encode('utf8')) + '=' + quote(str(v).encode('utf8')))
        return '&'.join(tp)

    @staticmethod
    def __getRequestUrl(api, query):
        return api + '?' + query

    def __getJSONResp(self, api, param):
        url = self.__getRequestUrl(api, self.__getFinalQuery(param))
        page = get_response(self.urlOpener, url)
        return json.loads(page)

    def __getTopicList(self, start=0, sort='created', top_type='no_top'):
        api = 'https://api.taptapdada.com/topic/v1/by-app'
        param = {
            'sort': sort,
            'type': top_type,
            'limit': self.pageLimit,
            'from': start
        }
        js = self.__getJSONResp(api, param)
        tlist = js['data']['list']
        ret = []
        for i in tlist:
            ret.append({
                'id': i['id'],
                'created_time': i['created_time'],
                'commented_time': i['commented_time'],
                'type': top_type,
                'comments': i['comments']
            })
        return ret

    def __getTopicDetail(self, tid):
        api = 'https://api.taptapdada.com/topic/v1/detail'
        param = {
            'id': tid
        }
        js = self.__getJSONResp(api, param)
        ret = {
            'topic_id': tid,
            'post_id': 0,
            'author_id': js['data']['topic']['author']['id'],
            'title': js['data']['topic']['title'].lower(),
            'content': html2Text(js['data']['first_post']['contents']['text']),
            'label_id': int(js['data']['topic']['group_label']['params']['group_label_id']),
            'elite': int(js['data']['topic']['is_elite']),
            'official': int(js['data']['topic']['is_official']),
            'created_time': js['data']['topic']['created_time'],
            'updated_time': js['data']['first_post']['updated_time'],
            'commented_time': js['data']['topic']['commented_time'],
            'comments': js['data']['topic']['comments'],
            'ups': js['data']['topic']['ups'],
            'downs': js['data']['topic']['downs']
        }
        return ret

    def __getReplyByPost(self, pid, topic, start=0, rets=None, order='asc', sort='position',
                         retrieve='all', time_created=0, check_exist=False):
        # retrieve 也可定义为获取次数(int) 获取数量为 次数 x self.pageLimit
        if isinstance(retrieve, int):
            retrieve -= 1
        api = 'https://api.taptapdada.com/post/v1/by-post'
        param = {
            'sort': sort,
            'order': order,
            'id': pid,
            'limit': self.pageLimit,
            'from': start,
            'show_topic': 0,
            'show_parent_post': 0
        }
        js = self.__getJSONResp(api, param)
        if rets is None:
            rets = []
        plist = js['data']['list']
        before = len(rets)
        for i in plist:
            # 如果回复时间早于给定时间 不予记录
            if time_created != 0 and i['created_time'] <= time_created:
                if order == 'asc':
                    continue
                elif order == 'desc':
                    break
            elif check_exist and self.__checkIfReplyExist(topic['topic_id'], i['id']):
                if order == 'asc':
                    continue
                elif order == 'desc':
                    break
            item = {
                'topic_id': topic['topic_id'],
                'post_id': i['id'],
                'author_id': i['author']['id'],
                'title': '',
                'content': html2Text(i['contents']['text']),
                'label_id': topic['label_id'],
                'elite': topic['elite'],
                'official': topic['official'],
                'created_time': i['created_time'],
                'updated_time': i['updated_time'],
                'commented_time': 0,
                'comments': i['comments'],
                'ups': i['ups'],
                'downs': i['downs']
            }
            rets.append(item)
        if len(rets) == before:
            return rets
        elif js['data']['next_page'] != '' and bool(retrieve):
            offset = start + self.pageLimit
            return self.__getReplyByPost(pid, topic, offset, rets, order, sort, retrieve, time_created, check_exist)
        return rets

    def __getReplyByTopic(self, topic, start=0, rets=None, order='asc', sort='position',
                          retrieve='all', time_created=0):
        # retrieve 也可定义为获取次数(int) 获取数量为 次数 x self.pageLimit
        if isinstance(retrieve, int):
            retrieve -= 1
        api = 'https://api.taptapdada.com/post/v3/by-topic'
        param = {
            'sort': sort,
            'order': order,
            'topic_id': topic['topic_id'],
            'limit': self.pageLimit,
            'from': start
        }
        js = self.__getJSONResp(api, param)
        if rets is None:
            rets = []
        plist = js['data']['list']
        before = len(rets)
        for i in plist:
            # 如果回复时间早于给定时间 不予记录
            if time_created != 0 and i['created_time'] <= time_created:
                if order == 'asc':
                    continue
                elif order == 'desc':
                    break
            item = {
                'topic_id': topic['topic_id'],
                'post_id': i['id'],
                'author_id': i['author']['id'],
                'title': '',
                'content': html2Text(i['contents']['text']),
                'label_id': topic['label_id'],
                'elite': topic['elite'],
                'official': topic['official'],
                'created_time': i['created_time'],
                'updated_time': i['updated_time'],
                'commented_time': 0,
                'comments': i['comments'],
                'ups': i['ups'],
                'downs': i['downs']
            }
            rets.append(item)
        if len(rets) == before:
            return rets
        elif js['data']['next_page'] != '' and bool(retrieve):
            offset = start + self.pageLimit
            return self.__getReplyByTopic(topic, offset, rets, order, sort, retrieve, time_created)
        return rets

    # by created_time For do_Data
    def __getTopicIDsByCreatedTime(self, time_created, start=0, rets=None, include_top=True):
        tList = []
        if include_top:
            tList = self.__getTopicList(start, top_type='top')
            self.debug_output('[data] top post list completed')
        tList.extend(self.__getTopicList(start))
        self.debug_output('[data] no_top post(created) list {}-{} completed'.format(start, start+self.pageLimit-1))
        if rets is None:
            rets = []
        before = len(rets)
        for i in tList:
            if i['created_time'] > time_created:
                rets.append(i)
            # 如果不是置顶帖 则确认处理完毕
            elif i['type'] != 'top':
                return rets
        if len(rets) == before:
            return rets
        return self.__getTopicIDsByCreatedTime(time_created, start+self.pageLimit, rets, False)

    # by commented_time For do_Update
    def __getTopicIDsByCommentedTime(self, time_commented, start=0, rets=None, include_top=True):
        tList = []
        if include_top:
            tList = self.__getTopicList(start, top_type='top')
            self.debug_output('[update] top post list completed')
        tList.extend(self.__getTopicList(start, 'commented'))
        self.debug_output('[update] no_top post(commented) list {}-{} completed'.format(start, start+self.pageLimit-1))
        if rets is None:
            rets = []
        before = len(rets)
        for i in tList:
            if i['commented_time'] > time_commented:
                rets.append(i)
            elif i['type'] == 'top':
                # 对于置顶帖 额外使用评论总数侦测楼中楼评论 (因为楼中楼评论不会更新主题的回复时间)
                cCount = self.__getTopicCommentCount(i['id'])
                if i['comments'] > cCount:
                    rets.append(i)
            # 如果不是置顶帖 则确认处理完毕
            elif i['type'] != 'top':
                return rets
        if len(rets) == before:
            return rets
        return self.__getTopicIDsByCommentedTime(time_commented, start+self.pageLimit, rets, False)

    def __checkIfTopicNeedUpdate(self, tid, time_commented, comments):
        sql = 'SELECT commented_time, comments FROM posts WHERE topic_id = {}'.format(tid)
        res = self.DBExecute(sql).fetchone()
        if res is None:
            return True
        # res 不为 NoneType
        elif res[0] < time_commented or res[1] < comments:
            return True
        return False

    def __insertData(self, data):
        tuples = self.__buildInsertTuple(data)
        columns = []
        for i in range(len(tuples[0])):
            columns.append('?')
        fin = ', '.join(columns)
        self.DBExecuteMany('REPLACE INTO posts VALUES ({})'.format(fin), tuples)

    def __getTopicCommentCount(self, tid):
        sql = 'SELECT comments FROM posts WHERE topic_id = {}'.format(tid)
        res = self.DBExecute(sql).fetchone()
        if res is not None:
            return res[0]
        return -1

    def __getTopicCommentedTime(self, tid):
        sql = 'SELECT commented_time FROM posts WHERE topic_id = {}'.format(tid)
        res = self.DBExecute(sql).fetchone()
        return res[0]

    def __checkIfReplyExist(self, tid, pid):
        sql = 'SELECT COUNT(*) FROM posts WHERE topic_id = {} AND post_id = {}'.format(tid, pid)
        res = self.DBExecute(sql).fetchone()
        if res[0] == 0:
            # self.debug_output('topic {} reply {} is new'.format(tid, pid))
            return False
        # self.debug_output('topic {} reply {} already exist'.format(tid, pid))
        return True

    def __getNewestReplyByTopic(self, topic, time_replied, num_want):
        outList = []
        # 先获取帖子最末的回复
        self.debug_output('[update] scan from bottom of topic...')
        endReplyList = self.__getReplyByTopic(topic, order='desc', time_created=time_replied)
        if len(endReplyList) > 0:
            self.debug_output('[update] bottom get new {}'.format(endReplyList))
        if len(endReplyList) >= num_want:
            return endReplyList

        outList.extend(endReplyList)
        # 尝试对最末的回复获取楼中楼
        for i in endReplyList:
            if i['comments'] > 0:
                self.debug_output('[update] scan new post in posts from bottom of topic...')
                popList = self.__getReplyByPost(i['post_id'], topic, order='desc', check_exist=True)
                outList.extend(popList)
                if len(popList) > 0:
                    self.debug_output('[update] bottom pop get new {}'.format(popList))
                if len(outList) >= num_want:
                    return outList

        # 获取点赞最多的100层 (通常很多人会选择回复此类内容)
        self.debug_output('[update] scan top 100 posts of topic...')
        upList = self.__getReplyByTopic(topic, order='desc', sort='ups', retrieve=10)
        for i in upList:
            # 检查楼中楼是否有新回复
            if i['comments'] > 0:
                popList = self.__getReplyByPost(i['post_id'], topic, order='desc', check_exist=True)
                # 有新回复，则该层也要更新
                if len(popList) > 0:
                    self.debug_output('[update] top 100 pop get new {}'.format(popList))
                    num_want += 1
                    outList.append(i)
                outList.extend(popList)
                if len(outList) >= num_want:
                    return outList

        # 获取最先回复的50层 (很多人也喜欢挤前排)
        self.debug_output('[update] scan first 50 posts of topic...')
        firstList = self.__getReplyByTopic(topic, order='asc', retrieve=5)
        for i in firstList:
            # 检查楼中楼是否有新回复
            if i['comments'] > 0:
                popList = self.__getReplyByPost(i['post_id'], topic, order='desc', check_exist=True)
                # 有新回复，则该层也要更新
                if len(popList) > 0:
                    self.debug_output('[update] first 50 pop get new {}'.format(popList))
                    num_want += 1
                    outList.append(i)
                outList.extend(popList)
                if len(outList) >= num_want:
                    return outList
        # 无论如何 返回数据
        return outList

    def __getTopicReplyRecursive(self, topic, rets=None):
        if rets is None:
            rets = []
        if topic['comments'] > 0:
            pList = self.__getReplyByTopic(topic)
            for j in pList:
                rets.append(j)
                # 判断回复是否有楼中楼
                if j['comments'] > 0:
                    popList = self.__getReplyByPost(j['post_id'], topic)
                    rets.extend(popList)
        return rets

    def __collectData(self, tids, force_update=False, try_selective_update=False):
        # 先检查一遍labels
        self.__collectLabelData()
        for i in tids:
            # 不需要更新则跳过
            if not self.__checkIfTopicNeedUpdate(i['id'], i['commented_time'], i['comments']) and not force_update:
                self.debug_output('[Topic update] skip {}'.format(i['id']))
                continue
            infList = []
            # 根据帖子ID 获取帖子内容 (主贴内容必须先更新)
            tDetail = self.__getTopicDetail(i['id'])
            infList.append(tDetail)
            self.debug_output('[update] retrieving reply of topic {}'.format(i['id']))
            # 对于新回复 是否采取增量更新的模式
            if try_selective_update:
                # 先获取数据库记录的评论条数
                comment_count = self.__getTopicCommentCount(i['id'])
                # 记录的评论数为 -1 代表数据库没有该记录 直接全量更新
                # 或者 该帖子的当前评论数量少于 200 条 直接全量更新即可
                if comment_count == -1 or i['comments'] <= 200:
                    self.debug_output('[update] no record or no more 200 using full update for topic {}'.format(i['id']))
                    infList.extend(self.__getTopicReplyRecursive(tDetail))
                else:
                    # 计算需要更新的条目数量
                    num_want = max(i['comments'] - comment_count, 0)
                    if num_want != 0:
                        self.debug_output('[update] selective update ENABLED for topic {}'.format(i['id']))
                        newReplyList = \
                            self.__getNewestReplyByTopic(tDetail, self.__getTopicCommentedTime(i['id']), num_want)
                        if len(newReplyList) >= num_want:
                            self.debug_output('[update] selective update SUCCEED for topic {}'.format(i['id']))
                            infList.extend(newReplyList)
                        else:
                            self.debug_output('[update] selective update FAILED for topic {}'.format(i['id']))
                            # 更新条目数量不符 全量更新
                            self.debug_output('[update] using full update for topic {}'.format(i['id']))
                            infList.extend(self.__getTopicReplyRecursive(tDetail))
                    else:
                        # 更新量为0可能是因为产生了删除评论 进行全量更新
                        self.debug_output('[update] some comments are missing, using full update for topic {}'.format(i['id']))
                        infList.extend(self.__getTopicReplyRecursive(tDetail))
            else:
                # 全量更新回复
                self.debug_output('[data] using full update for topic {}'.format(i['id']))
                infList.extend(self.__getTopicReplyRecursive(tDetail))
            # 每次扫描完一个帖子，记录一次
            # print(infList)
            self.__insertData(infList)
            self.debug_output('[update] topic {} updated'.format(i['id']))

    @staticmethod
    def __getDefaultTimestamp(days=7):
        td = get_today_datetime()
        dt = day_sub(td, days)
        return dt

    def __getLastCommentTimestamp(self):
        sql = 'SELECT MAX(commented_time) FROM posts'
        res = self.DBExecute(sql).fetchone()
        if res is not None:
            return res[0]
        return self.__getDefaultTimestamp(1)

    def __buildWhereStmt(self, add_where=True):
        stmt = []
        ###########
        # label (id|id,id) 用于帖子分区
        label = self.labelIDs
        if label is not None:
            li = ['label_id = ' + str(v) for v in self.labelIDs]
            stmt.append('( {} )'.format(' OR '.join(li)))
        ###########
        # topic_id
        topic = self.queryDict.get('tid')
        if topic is not None:
            stmt.append('topic_id = {}'.format(topic))
        ###########
        # created since (timestamp) 用于精确获取以发布时间为准的内容(主题+回复)
        timeCreated = self.queryDict.get('created_since')
        if timeCreated is not None:
            stmt.append('created_time > {}'.format(timeCreated))
        ############
        # created till (timestamp) 用于设定截至时间
        createdTill = self.queryDict.get('created_till')
        if createdTill is not None:
            stmt.append('created_time <= {}'.format(createdTill))
        ###########
        # updated since (timestamp) 用于精确获取近期发表/修改过的内容(主题+回复)
        timeUpdated = self.queryDict.get('updated_since')
        if timeUpdated is not None:
            stmt.append('updated_time > {}'.format(timeUpdated))
        ############
        # updated till (timestamp) 用于设定截至时间
        updatedTill = self.queryDict.get('updated_till')
        if updatedTill is not None:
            stmt.append('updated_time <= {}'.format(updatedTill))
        ############
        # commented since (timestamp) 用于精确获取近期被顶的主题帖
        timeCommented = self.queryDict.get('commented_since')
        if timeCommented is not None:
            stmt.append('commented_time > {}'.format(timeCommented))
        ############
        # commented till (timestamp) 用于设定截至时间
        commentedTill = self.queryDict.get('commented_till')
        if commentedTill is not None:
            stmt.append('commented_time <= {}'.format(commentedTill))
        ############
        # elite (0|1) 区分是否精华
        elite = self.queryDict.get('elite')
        if elite is not None:
            stmt.append('elite = {}'.format(int(bool(elite))))
        ############
        # official (0|1) 区分是否官方贴
        official = self.queryDict.get('official')
        if official is not None:
            stmt.append('official = {}'.format(int(bool(official))))

        # 合成 where 限制条件
        if add_where:
            if len(stmt) > 0:
                return ' WHERE {}'.format(' AND '.join(stmt))
            else:
                return ''
        else:
            return ' AND '.join(stmt)

    def __getAsText(self):
        where_stmt = self.__buildWhereStmt(True)
        li = self.DBExecute('SELECT title,content FROM posts {}'.format(where_stmt)).fetchall()
        allLine = []
        for i in li:
            if i[0] != '':
                allLine.append(i[0])
            allLine.append(remove_url(i[1]))
        return "\n".join(allLine)

    @staticmethod
    def __userDict():
        newWord = ('米哈游', '米忽悠', '洗地', '崩坏三', '崩坏3', '崩崩崩', '蹦蹦蹦', '米卫兵', '提瓦特', '蒙德城',
                   '不知道', '恰饭', '开放世界', '不可能', '荒野之息', '旷野之息', '真香', '评论区', '对线',
                   '还原神作', '既视感', '动作游戏', '后生仔', '找气受', '为什么', '大教堂', '蒙德',
                   '腾讯QQ', 'QQ游戏平台', 'QQ音乐', 'QQ网购', 'QQ商城', 'QQ飞车', 'QQ直播', 'QQ医生', 'QQ软件',
                   'QQ旋风', 'QQ拼音', 'QQ影音', 'QQ浏览器', 'QQ桌面', 'QQ手机', 'QQ词典', 'QQ影像', 'QQ工具条',
                   'QQ播客', 'QQ团购', 'QQ空间', 'QQ相册', 'QQ校友', 'QQ邮箱', 'QQ返利', 'QQ对战平台', 'QQ堂',
                   'QQ三国', 'QQ西游', 'QQ英雄杀', 'QQ幻想', 'QQ炫舞', 'QQ寻仙', 'QQ音速', 'QQ绿色征途', 'QQ农场',
                   'QQ牧场', 'QQ宝贝', 'QQ餐厅', 'QQ鱼塘')
        delWord = ('游戏', '玩家', '自己', '觉得', '就是', '不是', '可以', '什么', '这么', '一样', '所以',
                   '我觉', '的话', '没有', '现在', '但是', '知道', '真的', '还是', '这个', '一个', '楼主', '一点',
                   '不会', '出来', '怎么', '可能', '如果', '我们', '你们', '这样', '应该', '这游戏', '别人', '毕竟',
                   '一下', '很多', '时候', '这种', '因为', '而且', '不过', '为什么', '帖子', '还有', '其实', '有人',
                   '大家', '看到', '那么', '只是', '然后', '他们', '或者', '比如', '最后', '开始', '只有', '要是',
                   '是因为', '其他', '多少', '这些', '一些', '只要', '不要', '目前', '直接', '个人', '一款', '看看',
                   '已经', '那些', '而已', '好像', '真是', '几个', '之前', '地方', '所谓', '本来', '其他', '顺便'
                   '对于', '这里', '来说', '东西', '不能', '那个', '确实', '问题', '链接', '回复', '不知道', '这次',
                   '传说', '不知')
        for i in newWord:
            jieba.suggest_freq(i, True)
        for i in delWord:
            jieba.del_word(i)

    def do_Data(self):
        dt = self.queryDict.get('created_since')
        if dt is None:
            # default 7 day ago
            day = self.queryDict.get('day')
            if day is None:
                day = 7
            dt = self.__getDefaultTimestamp(int(day))
        tIDs = self.__getTopicIDsByCreatedTime(dt)
        self.__collectData(tIDs, try_selective_update=True)
        self.content['created_since'] = dt

    def do_Countword(self):
        allLine = self.__getAsText()
        self.__userDict()
        word = self.queryDict.get('word')
        if word is None:
            word = 200
        keywords = jieba.analyse.extract_tags(allLine, int(word), withWeight=True)
        allWords = jieba.cut(allLine, cut_all=False)
        ct = Counter(allWords)
        fin = {k: ct[k] for (k, v) in keywords}
        self.content['data'] = fin

    def do_Lower(self):
        sql = 'SELECT topic_id,post_id, title, content FROM posts'
        res = self.DBExecute(sql).fetchall()
        uSql = 'UPDATE posts SET title = ?, content = ? WHERE topic_id = ? AND post_id = ?'
        for i in res:
            title = i[2].lower()
            content = i[3].lower()
            self.DBExecute(uSql, (title, content, i[0], i[1]))

    # def do_Wordcloud(self):
    #     allLine = self.__getAsText()
    #     self.__userDict()
    #     keywords = jieba.analyse.extract_tags(allLine, 200, withWeight=True)
    #     allWords = jieba.cut(allLine, cut_all=False)
    #     ct = Counter(allWords)
    #     d = {k: ct[k] for (k, v) in keywords}
    #     font = r'fonts/simhei.ttf'
    #     wc = WordCloud(
    #         font_path=font,
    #         background_color='white',
    #         max_words=200,
    #         max_font_size=150,
    #         width=800,
    #         height=1000,
    #     )
    #     wc.generate_from_frequencies(d)
    #     wc.to_file('fin.png')

    # def do_Plt(self):
    #     allLine = self.__getAsText()
    #     self.__userDict()
    #     words = jieba.analyse.extract_tags(allLine, 30, withWeight=True)
    #     allWords = jieba.cut(allLine, cut_all=False)
    #     ct = Counter(allWords)
    #     font = pltf.FontProperties(fname=r'fonts/simhei.ttf')
    #     xD = []
    #     yD = []
    #     plt.figure(figsize=(21, 9))
    #     for i in words:
    #         xD.append(i[0])
    #         yD.append(ct[i[0]])
    #
    #     plt.bar(range(len(yD)), yD, tick_label='')
    #     ind = arange(len(xD))
    #     plt.xticks(ind, xD, FontProperties=font)
    #
    #     plt.ylabel(u'出现次数', FontProperties=font)
    #     plt.title(u'近7天TapTap高频词(' + self.__getLabelStr() + ')统计', FontProperties=font)
    #     plt.savefig('plt.png')

    def do_Json(self):
        where_stmt = self.__buildWhereStmt(True)
        li = self.DBExecute('SELECT * FROM posts {}'.format(where_stmt)).fetchall()
        allJSON = []
        for i in li:
            allJSON.append({
                'topic_id': i[0],
                'post_id': i[1],
                'author_id': i[2],
                'title': i[3],
                'content': i[4],
                'label': i[5],
                'created_time': i[8],
                'updated_time': i[9],
                'commented_time': i[10],
                'comments': i[11],
                'ups': i[12],
                'downs': i[13]
            })
        self.content['data'] = allJSON

    def do_Update(self):
        dt = self.queryDict.get('commented_since')
        if dt is None:
            dt = self.__getLastCommentTimestamp()
        tIDs = self.__getTopicIDsByCommentedTime(int(dt))
        self.__collectData(tIDs, True, True)
        self.content['commented_since'] = dt

    def do_Labels(self):
        sql = 'SELECT label_id, label_name FROM labels'
        res = self.DBExecute(sql).fetchall()
        labelDict = {i[0]: i[1] for i in res}
        self.content['labels'] = labelDict


