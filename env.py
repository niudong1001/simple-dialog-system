# -*- coding:utf-8 -*-

# 本py代表环境，其需要做的是：
# 1.初始化state
# 2.接收agent的action，在这个基础上生成user回答,并结合agent的action与用户回答给出新的state与reward

import re
import random
from flask import Flask, render_template
from flask_socketio import SocketIO, emit,send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# 资源路径
slot_file_path="./resources/SlotValues.txt"
sys_res_path="./resources/SysResponses.txt"
usr_res_path="./resources/UsrResponses.txt"

# 去掉单词中的特殊符号的正则表达式
reg=r'(!|\?|\.|\"|,)+$'
# reg_list=["!","?","."," ",'"']
env=None # 环境类

# 读取文件
def read_file(file_path):
    with open(file_path,"r") as f:
        lines=f.readlines() # 按行读取,返回list
        # for line in lines:
        #     print(line.strip()) # 打印并去除行末尾\n
        return lines

def get_key_from_index(dic,index): # 通过index找value
    if index <= len(dic)-1:
        keys=dic.keys() # 获得list
        key=keys[index]
        return key
    else:
        return None

def get_vocabulary():
    # 读取资源
        slot_list=read_file(slot_file_path)
        sys_list=read_file(sys_res_path)
        usr_list=read_file(usr_res_path)
        # 获得vocabulary
        vocabulary=[]
        # 获得slot中的单词
        slot_words=[] # slot的单词
        for line in slot_list:
            line=line.strip() # 去尾部\n
            slot_words+=line.split(":")[1][1:-1].split("|") #分割加入，但未去重 reasonably priced会出错
        # print slot_words
        # 获得sys中的单词
        sys_words_unhandle=[] # sys的单词未处理
        sys_words=[] # sys的单词
        for line in sys_list:
            line=line.strip() # 去尾部\n
            if line: # 非空行
                sys_words_unhandle+=line.split(":")[1][1:-1].split(" ")
        for index,word in enumerate(sys_words_unhandle):
            if word.find("$") == -1: # 不存在$符号
                sys_words.append(re.sub(reg,"",word)) # 移除单词符号项目
        # print sys_words
        # 获得usr中的单词
        usr_words_unhandle=[]
        usr_words=[]
        for line in usr_list:
            line=line.strip()
            if line:
                sentence=line.split(":")[1]
                if sentence.find("(")==-1: # 是回答句子
                    sentences=sentence.split("|")
                    for s in sentences:
                        s=s[1:-1] # 两边的""
                        usr_words_unhandle+=s.split(" ")
        for index,word in enumerate(usr_words_unhandle):
            if word.find("$") == -1: # 不存在$符号
                usr_words.append(re.sub(reg,"",word)) # 移除单词符号项目
        # print usr_words
        vocabulary+=slot_words+sys_words+usr_words
        vocabulary=list(set(vocabulary))
        vocabulary.sort()
        print("词汇列表如下，共:",len(vocabulary),"个单词")
        print(vocabulary)
        print("  ")
        return vocabulary

def get_words(sentence):# 根据句子获得单词列表
    words=sentence.split(" ")
    for i,word in enumerate(words):
        words[i]=re.sub(reg,"",word) # 异常特殊字符
    # print words
    return words

class Slot(object): # slot管理
    def __init__(self):
        slot_list=read_file(slot_file_path)
        self.slot_dic={} # 存储所有的slot
        self.slot_appeared_dic={} # 存储会话中出现的slot
        for line in slot_list:
            line=line.strip().split(":")
            self.slot_dic[line[0]]=line[1][1:-1].split("|")
        # print  self.slot_dic

    def random_init_slot(self,sentence): # 随机初始化句子中的变量
        for word in get_words(sentence):
            if word in self.slot_dic:
                v=self.slot_dic[word] # 获得值
                n=random.randint(0, len(v)-1) # 获得随机数
                sentence=sentence.replace(word,v[n]) # 获得随机slot的值
                self.slot_appeared_dic[word]=v[n] # 记录会话中出现的slot
        return sentence

    def replace_slot(self,sentence): # 用会话中出现的slot代替
        flag=True # 是否全部能被slot_appeared_dic中的slot替换
        for word in get_words(sentence):
            if word.find("$") !=-1: # 是变量
                if word in self.slot_appeared_dic:
                    sentence=sentence.replace(word,self.slot_appeared_dic[word]) # 发现则替换
                else:
                    flag=False
        if flag:
            return sentence
        else:
            return self.random_init_slot(sentence) # 再随机初始化

class State(object): #状态维护类
    def __init__(self,vocabulary): # 更新状态
        self.vocabulary=vocabulary
        self.init_state()

    def init_state(self):
        self.state=[0]*len(self.vocabulary) # 初始化为全0

    def update_state(self,words,use_random): #根据句子更新env状态
        for word in words:
            index=self.vocabulary.index(word)
            if index!=-1:
                if use_random:
                    self.state[index]=round(random.random(),2) # 随机值
                else:
                    self.state[index]=1
        return self.state

class Action(object): # 动作类
    def __init__(self):
        # 读取sys
        sys_list=read_file(sys_res_path)
        self.sys_dic={} # 创建sys_dic
        self.sys_list=[] # 创建sys_list
        for line in sys_list:
            line=line.strip()
            if line:
                line=line.split(":")
                self.sys_list.append(line[0]) # 放入list
                self.sys_dic[line[0]]=line[1][1:-1]
        print("Agent可选的action列表:")
        print(self.sys_list)
        # 读取usr
        usr_list=read_file(usr_res_path)
        self.usr_dic={} # 创建sys_dic
        for line in usr_list:
            line=line.strip()
            if line:
                line=line.split(":")
                key=line[0] # 获得key
                value=line[1] # 获得value
                self.usr_dic[key]=value.split("|")


    def get_sys_action(self,key): # 获得sys action
        return self.sys_dic[key]

    def get_usr_action(self,key): # 获得usr action
        v=self.usr_dic[key]
        if isinstance(v,list): # 有很多action可以选择
            n=random.randint(0, len(v)-1) # 获得随机数
            r=v[n]
        else:
            r=v
        if r.find("(") ==-1:
            return r[1:-1]
        else:
            return self.get_usr_action(r)


# 环境类
class Env(object):
    def __init__(self):
        self.vocabulary=get_vocabulary() # 获取到词汇表
        self.num_of_state=len(self.vocabulary) # 更新state数目
        self.slot=Slot() # 创建slot类
        self.action=Action() # 创建action类
        self.num_of_sys_action=len(self.action.sys_dic) # 更新action数目
        self.state=State(self.vocabulary) # 初始化state类
        self.all_loop=100 # 所有的loop
        self.count_loop=1 # 计算已经有的loop
        self.finished_all_loop=False # 完成所有对答
        self.finished_one_loop=False # 完成一组对答
        self.reward=0 # reward初始化
        # print "初始化state:",self.state.state
        # print " "
        # test={ # 模拟agent的操作
        #     "key":"Request(hmihy)",
        #     "text":"How can I help you?"
        # }
        # self.update_env(test)

    def update_env(self,action_index): # 更新env状态
        # sys处理
        sys_key=self.action.sys_list[action_index] # 获得sys的key
        sys_sentence=self.action.get_sys_action(sys_key) # 获得sys的未处理句子
        self.sys_sentence=self.slot.replace_slot(sys_sentence) # 用slot填充
        print(" ")
        print("sys 选择action：",sys_key)
        # usr处理
        if sys_key.find("ImpConfirm")!=-1 or sys_key.find("Retrieve")!=-1:
            self.user_sentence=""
        elif sys_key.find("closing")!=-1 or sys_key.find("known")!=-1:
            self.user_sentence=""
            self.finished_one_loop=True
            self.count_loop+=1 # loop+1
            if self.count_loop>self.all_loop:
                self.finished_all_loop=True
        else:
            user_sentence=self.action.get_usr_action(sys_key) # 获取用户回答
            self.user_sentence=self.slot.replace_slot(user_sentence) # 用随机slot填充
        # 打印

        print("agent询问:",self.sys_sentence)
        self.state.update_state(get_words(self.sys_sentence),False) # 更新agent回答到state
        if self.user_sentence: # 有回答
            print("user回答:",self.user_sentence)
            self.state.update_state(get_words(self.user_sentence),True) # 更新user回答到state
        print("state更新为:",self.state.state)
        if self.user_sentence.find("Yes")!=-1 or self.user_sentence.find("I did")!=-1:
            self.reward=1
        else:
            self.reward=0
        print("reward为:",self.reward)
        if self.finished_one_loop:
            print("******************完成本轮对话*******************************************************")
            self.finished_one_loop=False

# 接收来自客户端的信息(string)
@socketio.on('message', namespace='/test')
def test_message(message):
    # print message
    if message!="brain inited,wait state and reward...":
        if not env.finished_all_loop: # 未完成整次对话
            action_index=message["action"]
            env.update_env(action_index)
            send({
                "state":env.state.state,
                "reward":env.reward,
                "finished":False
            })
        else:
            send({
                "finished":True
            })

@socketio.on('connect', namespace='/test')
def test_connect():
    print('Client connected')
    send({
        "num_of_state":env.num_of_state,
        "num_of_sys_action":env.num_of_sys_action
    })

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')

# 启动调用
if __name__=="__main__":
    env=Env()
    socketio.run(app=app,host="127.0.0.1",port=9999)
