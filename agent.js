
//本js代表agent，其需要做的是：结合env的state与reward运用DQN生成action向量
// 为避免错误，需要进入node_modules\convnetjs下找到deepqlearn.js中加入以下
/*
var convnetjs = require(__dirname+'/convnet.js');
var cnnutil = require(__dirname+'/util.js');
*/

// 引入库文件
var convnetjs=require("./node_modules/convnetjs/build/convnet-min");
var deepqlearn = require('./node_modules/convnetjs/build/deepqlearn');
var fs = require('fs');

let inited=false; // 是否初始化了
let num_of_state=0; // state 的个数
let num_of_sys_action=0; // action的数目

let brain=null; // 大脑

var temporal_window = 1; // amount of temporal memory. 0 = agent lives in-the-moment :)
var network_size = 0;

// the value function network computes a value of taking any of the possible actions
// given an input state. Here we specify one explicitly the hard way
// but user could also equivalently instead use opt.hidden_layer_sizes = [20,20]
// to just insert simple relu hidden layers.
var layer_defs = [];

// options for the Temporal Difference learner that trains the above net
// by backpropping the temporal difference learning rule.
var tdtrainer_options = {learning_rate:0.001, momentum:0.0, batch_size:64, l2_decay:0.01};

var opt = {};
opt.temporal_window = temporal_window;
opt.experience_size = 30000;
opt.start_learn_threshold = 1000;
opt.gamma = 0.7;
opt.learning_steps_total = 200000;
opt.learning_steps_burnin = 3000;
opt.epsilon_min = 0.05;
opt.epsilon_test_time = 0.05;
opt.layer_defs = layer_defs;
opt.tdtrainer_options = tdtrainer_options;

var socket = require('socket.io-client')('http://localhost:9999/test');

// 连接了
socket.on('connect', function(){
    console.log("连接到服务器了..."); // 'G5p5...'
    // socket.send({a:"信息测试"});
});
// 获得数据
socket.on('message', function(data){
    if(inited){
        // console.log(data);
        if(!data.finished){
            let action=getAction(data.state,data.reward);
            // console.log(action);
            socket.send({
                action:action
            })
        }
        else{
            console.log("对话结束...")
            savePolicy(brain); 

        }
    }
    else{
        inited=true;
        num_of_state=data.num_of_state;
        num_of_sys_action=data.num_of_sys_action;
        console.log("初始化...")
        console.log("state数目:",num_of_state);
        console.log("action数目:",num_of_sys_action);
        console.log("对话开始...")
        initOpt(num_of_state,num_of_sys_action);
        brain=new deepqlearn.Brain(num_of_state, num_of_sys_action,opt); // 用输入与输出数目初始化
        loadPolicy(brain); //加载policy
        socket.send("brain inited,wait state and reward...");
        let start_action_index=Math.floor(Math.random()*8); // 随机初始化
        socket.send({
            action:start_action_index
        })
    }
});
// 断开连接
socket.on('disconnect', function(){
    console.log("服务器断开连接了..."); 
});

function initOpt(num_inputs,num_actions){ // 初始化参数
    var network_size = num_inputs*temporal_window + num_actions*temporal_window + num_inputs;
    layer_defs.push({type:'input', out_sx:1, out_sy:1, out_depth:network_size});
    layer_defs.push({type:'fc', num_neurons: 50, activation:'relu'});
    layer_defs.push({type:'fc', num_neurons: 50, activation:'relu'});
    layer_defs.push({type:'regression', num_neurons:num_actions});
}

function getAction(state,reward){
    var action = brain.forward(state);
    brain.backward(reward); // <-- learning magic happens here
    return action;
}

function savePolicy(brain){
    var j = brain.value_net.toJSON();
	var text = JSON.stringify(j);
	var file2Save = "./output/policy.json";
	fs.writeFile(file2Save, JSON.stringify(text, null, 4), function(err) {
		if(err) throw err;
		console.log("Saved policy at"+file2Save);
	});
}

function loadPolicy(brain) {
	var file2Read = "./output/policy.json";
	var text = require(file2Read);
	var j = JSON.parse(text);
	brain.value_net.fromJSON(j); 
	console.log("Network initialised!");
}


