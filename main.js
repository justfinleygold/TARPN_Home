$(document).ready(function(){

// var txt_monitor = $('#txt_monitor');
var txt_node = $('#txt_node');
var txt_chat = $('#txt_chat');
var strMessage = "";
var socket = new WebSocket("ws://" + location.hostname + ":8085/ws");

socket.onopen = function(){  
   localStorage.setItem("lastTimeReceived", +new Date); //reset time since last receive
   console.log("Connected."); 
}; 

socket.onmessage = function (message) {
   var datLastTimeReceived; 
   var datCurTimeReceived; 
   var intAudioTimeOut = 300000; // for audio tone. default of 5 minutes
   //console.log("Received: " + message.data)
   if (message.data.charAt(0) == "^") {
	// ^ in first character denotes passing in data rather than text
	var strVars = message.data.substring(1,message.data.length);
 	var objVars = JSON.parse(strVars);
	document.getElementById('lblNode').innerHTML = objVars.NodeName;
	document.getElementById('lblCall').innerHTML = objVars.CallSign;
	document.getElementById('lblPort1').innerHTML = objVars.Port1;
	document.getElementById('lblPort2').innerHTML = objVars.Port2;
	document.getElementById('lblPort3').innerHTML = objVars.Port3;
	document.getElementById('lblPort4').innerHTML = objVars.Port4;
   } else if (message.data.charAt(0) == "~") {
 	// ~ in first character denotes passing in state flags
	var strVars = message.data.substring(1,message.data.length);
	var objVars = JSON.parse(strVars);
	if (objVars.ChatConnected == "0") {
	    document.getElementById('btn_chat_join').disabled = false;
	    document.getElementById('btn_chat_leave').disabled = true;
	}
	else if (objVars.ChatConnected == "1") {
	    document.getElementById('btn_chat_join').disabled = true;
	    document.getElementById('btn_chat_leave').disabled = false;
	}	

   } else if (message.data.charAt(0) == "`") {
 	// ` in first character denotes passing in crowd text history
	var strVars = message.data.substring(1,message.data.length);
	var objVars = JSON.parse(strVars);
	document.getElementById('txt_chat').innerHTML = objVars.ChatHistory
	
//   } else if (message.data.charAt(0) == "!") {
//        // ! in first character denotes monitor text
//	txt_monitor.append(message.data.substring(1));
//	if (txt_monitor.html().length >= 8000) {
	   // remove from front if too long
//           txt_monitor.html(txt_monitor.html().slice(txt_monitor.html().length-8000));
//	}  
     	
 	// scroll to bottom
//   	var textarea = document.getElementById('txt_monitor');
//	textarea.scrollTop = textarea.scrollHeight;
   } else if (message.data.charAt(0) == "@") {
        // @ in first character denotes chat command
	datCurTimeReceived = new Date();
   	datLastTimeReceived = new Date(parseInt(localStorage.getItem("lastTimeReceived")));
    	//console.log("Time: " + datCurTimeReceived);
   	//console.log("Last: " + datLastTimeReceived);
   	//console.log("Diff: " + (datCurTimeReceived - datLastTimeReceived));
   	//var boolFocus = document.hasFocus()
   	//console.log("Focus: " + boolFocus);
   	if ((document.hasFocus() == false) || (datCurTimeReceived - datLastTimeReceived > intAudioTimeOut)) {
  		// play a tone
  		var audio = document.getElementsByTagName("audio")[0];
   		audio.play();
   	}
  	localStorage.setItem("lastTimeReceived", +new Date);
	txt_chat.append(message.data.substring(1));

	if (txt_chat.html().length >= 8000) {
	    //remove from front if too long
           txt_chat.html(txt_chat.html().slice(txt_chat.html().length-8000));
	}  
        
  	// scroll to bottom
   	var textarea = document.getElementById('txt_chat');
	textarea.scrollTop = textarea.scrollHeight;
    //} else if (message.data.charAt(0) == ":") {
    //    // : denotes shell command
    //	shell_text.append(message.data.substring(1).replace(/\r\n|\r|\n/g,"<br>"));
    //	shell_text.append($('<br/>'));
   } else {
	// node window
	txt_node.append(message.data);

	if (txt_node.html().length >= 8000) {
	   //remove from front if too long
           txt_node.html(txt_node.html().slice(txt_node.html().length-8000));
	}  
 	
   	// scroll to bottom
   	var textarea = document.getElementById('txt_node');
	textarea.scrollTop = textarea.scrollHeight;
   }
};

socket.onclose = function(){
  console.log("Disconnected");
};

var sendMessage = function(message) {
   localStorage.setItem("lastTimeReceived", +new Date); //reset time since last receive
   //console.log("Sending:" + message.data);
   socket.send(message.data);
};

// GUI Stuff

// send a node command to the serial port
$("#btn_node_send").click(function(event){
  event.preventDefault();
  sendNodeTextToNode();
});

// run after a CR
$("#txt_node_send").submit(function(event) {
  event.preventDefault();
  sendNodeTextToNode();
});

function sendNodeTextToNode() {
  var cmd = $('#txt_node_send').val();
  if (cmd != "") {
     sendMessage({ 'data' : cmd});
  }
  $('#txt_node_send').val("");
     
  // Add line to the Sent dropdown
  var selNodeSent = document.getElementById("sel_node_sent");
  var option = document.createElement("option");
  option.text = cmd;
  selNodeSent.add(option);
  selNodeSent.selectedIndex = selNodeSent.length-1;
  if (selNodeSent.length == 1) {
     document.getElementById('lbl_last_node_sent').innerHTML = cmd + ' (Up arrow to recall)';
  }
  else {
     document.getElementById('lbl_last_node_sent').innerHTML = cmd;
  }
};

$('#sel_node_sent').change(function(){
 $('#txt_node_send').val($(this).val());
});

$('#btn_node_clear').click(function(event){
  event.preventDefault();
  txt_node.empty();
});

$('#btn_node_reconnect').click(function(event){
  event.preventDefault();
  sendMessage({ 'data' : 'RECONNECT!'});
});

// send a chat command to the serial port
$("#btn_chat_send").click(function(event){
  event.preventDefault();
  sendChatTextToNode();
});

// run after a CR
$("#txt_chat_send").submit(function(event) {
  event.preventDefault();
  sendChatTextToNode();
});

function sendChatTextToNode(){
  var cmd = '@' + $('#txt_chat_send').val();
  if (cmd != "@") {
     sendMessage({ 'data' : cmd});
     $('#txt_chat_send').val("");
     
     // Add line to the Sent dropdown
     var selChatSent = document.getElementById('sel_chat_sent');
     var option = document.createElement('option');
     option.text = cmd.substring(1);
     selChatSent.add(option);
     selChatSent.selectedIndex = selChatSent.length-1;
     
     if (selChatSent.length == 1) {
	document.getElementById('lbl_last_chat_sent').innerHTML = cmd.substring(1) + ' (Up arrow to recall)'
     }
     else {
        document.getElementById('lbl_last_chat_sent').innerHTML = cmd.substring(1);
     }
  }
}

document.onkeydown = function(e) {
    var blContinue = 0;
    if (document.activeElement == document.getElementById("txt_chat_send")) {
	var selSent = document.getElementById("sel_chat_sent");
        var txtSend = $('#txt_chat_send');
        blContinue = 1;
    }
    else if (document.activeElement == document.getElementById("txt_node_send")) {
	var selSent = document.getElementById("sel_node_sent");
        var txtSend = $('#txt_node_send');
        blContinue = 1;
    }
    if (blContinue == 1) { 
        if (e.keyCode == '38') { //up arrow       
	    if (selSent.selectedIndex > -1) {
		if (txtSend.val() == "") {
		   txtSend.val(selSent.value); 
		}
		else if ((txtSend.val() == selSent.value) && 
			 (selSent.selectedIndex > 0)) {
	           selSent.selectedIndex = selSent.selectedIndex - 1;
	           txtSend.val(selSent.value);
		}
	    }
        }
        else if (e.keyCode == '40') { //down arrow       
	    if (selSent.selectedIndex > -1) { // dropdown not empty
	        if (selSent.selectedIndex < selSent.length-1) {
		    if (txtSend.val() == "") {
		    	txtSend.val(selSent.value);
		    }
		    else if (txtSend.val() == selSent.value) {
 		        selSent.selectedIndex = selSent.selectedIndex + 1;
		        txtSend.val(selSent.value);
		    }
		}
	    }

        }
    }
}

$('#sel_chat_sent').change(function(){
 $('#txt_chat_send').val($(this).val());
});

$('#btn_chat_clear').click(function(event){
  event.preventDefault();
  txt_chat.empty();
});

$('#btn_chat_join').click(function(event){
  event.preventDefault();
  sendMessage({ 'data' : '@C CROWD S'});
  $('#txt_chat_send').focus();
 });

$('#btn_chat_leave').click(function(event){
  event.preventDefault();
  sendMessage({ 'data' : '@/B'});
  sendMessage({ 'data' : '@B'});
});

$('#btn_chat_reconnect').click(function(event){
  event.preventDefault();
  sendMessage({ 'data' : '@RECONNECT!'});
});

//$('#btn_monitor_clear').click(function(event){
//  event.preventDefault();
 // txt_monitor.empty();
//});

$('#btnShutdown').click(function(){
  sendMessage({ 'data' : '\\X'});
});
});
