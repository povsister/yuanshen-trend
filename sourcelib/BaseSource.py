from sourcelib.basiclib import *
from abc import ABC, abstractmethod
from json import dumps
from sqlite3 import connect, OperationalError


class BaseSource(ABC):

    def __init__(self, parsed_url, query):
        self.content = {'msg': 'You should fill up this dict as final output'}
        self.parsedURL = parsed_url
        self.queryDict = query
        self.urlOpener = get_urlopener_with_cookie(self.cookie_file_name())
        self.DBConn = self.__getDBConn()
        self.DBConn.isolation_level = None

    @abstractmethod
    def cookie_file_name(self):
        pass

    def debug_output(self, msg):
        if self.debug is None or self.debug is True:
            print('<class {}>'.format(self.__class__.__name__), msg)

    def sqlite_file_name(self):
        return 'data/' + self.__class__.__name__ + '/data.db'

    def __do_default(self):
        if self.queryDict.get('action') is not None:
            self.content['msg'] = 'action [{}] not implemented!'.format('do_' + self.queryDict.get('action').capitalize())
        else:
            self.content['msg'] = 'No action specified!'

    # should be triggered manually in child class !
    def do_action(self):
        try:
            eval('self.do_' + self.queryDict.get('action').capitalize())()
            self.content['msg'] = 'action [{}] triggered!'.format('do_' + self.queryDict.get('action').capitalize())
        except Exception:
            traceback.print_exc()
            self.__do_default()

    def __getDBConn(self):
        try:
            return connect(self.sqlite_file_name())
        except OperationalError:
            import os
            t = self.sqlite_file_name().split('/')
            t = t[:len(t)-1]
            os.makedirs('/'.join(t))
            return self.__getDBConn()

    def DBExecute(self, sql, data=None):
        if data is None:
            return self.DBConn.execute(sql)
        return self.DBConn.execute(sql, data)

    def DBExecuteMany(self, sql, data):
        return self.DBConn.executemany(sql, data)

    def getJSON(self):
        return dumps(self.content, ensure_ascii=False, indent=4).encode('utf8')

