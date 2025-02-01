<script setup>
import { ref } from 'vue'
import HelloWorld from './components/HelloWorld.vue'

const message = ref('対戦相手を待っています');
const inputMessage = ref('');
const me = {
    name: 'player1',
    point: 0
}
const opponent = {
    name: 'player2',
    point: 0
}

var socket = new WebSocket("wss://bgzy33vu14.execute-api.ap-northeast-1.amazonaws.com/prod/");

socket.onopen = function() {
    console.log("接続できました！");
};

socket.onmessage = function(e) {
    console.log(e.data);
};

function send() {
    console.log("送信しました");
    socket.send(JSON.stringify(
        {
            "action":"default",
            "data": inputMessage.value
        }
    ));
    inputMessage.value = "";
};

</script>

<template>
  <main>
    <div id="left">
        画面
    </div>
    <div id="right">
        <div id="right-top">{{ me.name }}: {{ me.point }}</div>
        <div id="right-middle">{{ opponent.name }}: {{ opponent.point }}</div>
        <div id="next-hands">次の手</div>
        <div id="right-bottom">{{ message }}</div>
        <div id="input">
            <input id="inp" type="text" v-model="inputMessage" />
            <button @click="send">送信</button>
        </div>
    </div>
    <div id="output"></div>
  </main>
</template>

<style scoped>
main {
  display: flex;
  width: 80rem;
  height: 50rem;
  flex-direction: row;
}

#left {
    display: flex;
    flex-direction: column;
    width: 70%;
    height: 100%;
    background-color: #f0f0f0;
}

#right {
    display: flex;
    flex-direction: column;
    width: 30%;
    height: 100%;
    color: black;
}

#right-top {
    display: flex;
    background-color: lightcyan;
    height: 10%;
}

#right-middle {
    display: flex;
    background-color: cornsilk;    
    height: 10%;
}

#right-bottom {
    display: flex;
    background-color: lightpink;
    height: 30%;
}

#next-hands {
    display: flex;
    background-color: palegoldenrod;
    height: 50%;
}

</style>
