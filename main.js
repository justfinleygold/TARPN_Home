$(document).ready(function () {
	var txt_info = $("#txt_info");
	var txt_node = $("#txt_node");
	var txt_chat = $("#txt_chat");
	var strMessage = "";
	var socket = new WebSocket("ws://" + location.hostname + ":8085/ws");
	const NODE_PREFIX = '\x10';
	const CHAT_PREFIX = '\x11';
	const HIDDEN_PREFIX = '\x12';
	const DATA_PREFIX = '\x13';
	var intNodeCode = 16;
	var intChatCode = 17;
	var intHiddenCode = 18;	
	var intDataCode = 19;
	var strBBS_list_JSON = '';
	var lst_BBS_msg = [];
	var BBS_Table;
	
	document.getElementById("txt_chat").addEventListener("focus", turnOffVisualAlert);
	document.getElementById("txt_chat_send").addEventListener("focus", turnOffVisualAlert);
	document.getElementById("btn_chat").addEventListener("click", turnOffVisualAlert);

	function turnOffVisualAlert() {
		if (document.getElementById("btn_chat").className.indexOf("yellow") > -1) {
			document.getElementById("btn_chat").className = 
			document.getElementById("btn_chat").className.replace("w3-yellow", "myMainColor");  
		}
	}		

	var chat_audio = document.createElement('audio');
    chat_audio.setAttribute('src', "static/tarpn_tone.mp3");
    chat_audio.setAttribute('src', "static/tarpn_tone.wav");

	var bbs_audio = document.createElement('audio');
    bbs_audio.setAttribute('src', "static/tarpn_mail.mp3");
    bbs_audio.setAttribute('src', "static/tarpn_mail.wav");
  
	function findArrayMatch(element, strIn) {
	  return element == strIn;
	}
	socket.onopen = function () {
		localStorage.setItem("lastTimeReceived", +new Date()); //reset time since last receive
		readCommands(); // get JSON into dropdowns
		console.log("Connected.");
	};

	// read the dropdown commands
	function readCommands() {
		let sel_chat_cmds = document.getElementById('sel_chat_cmds');
		sel_chat_cmds.length = 0;
		let defaultOption = document.createElement('option');
		defaultOption.text = 'Choose Command';
		sel_chat_cmds.add(defaultOption);
		sel_chat_cmds.selectedIndex = 0;
		
		let sel_node_cmds = document.getElementById('sel_node_cmds');
		sel_node_cmds.length = 0;
		let defaultOption2 = document.createElement('option');
		defaultOption2.text = 'Choose Command';
		sel_node_cmds.add(defaultOption2);
		sel_node_cmds.selectedIndex = 0;

		const url = 'static/TARPN_Commands.json';

		const request = new XMLHttpRequest();
		request.open('GET', url, true);

		request.onload = function() {
			if (request.status === 200) {
				const data = JSON.parse(request.responseText);
				let option;
				for (let i = 0; i < data.length; i++) {
					option = document.createElement('option');
					option.text = data[i].Display;
					option.value = data[i].Send;
					if (data[i].Tier == 'Chat') {
						sel_chat_cmds.add(option);
					}
					else if (data[i].Tier == 'Node') {
						sel_node_cmds.add(option);
					}
				}
		   } else {
			// Reached the server, but it returned an error
			console.error('An error occurred fetching the JSON from ' + url);
		  }   
		}

		request.onerror = function() {
			console.error('An error occurred fetching the JSON from ' + url);
		};

		request.send();			
	}
	
	function stripAwayBackFromText(strIn) {
		var str = strIn;
		
		// use regex to find and strip
		str = str.replace(/\d\d:\d\d ..: .{4,7} : away<br>/ig,'');
		str = str.replace(/<span style="color:#......;font-weight:bold">\d\d:\d\d ..: .{4,16} : away<\/span><br>/ig,'');
		str = str.replace(/\d\d:\d\d ..: .{4,7} : afk<br>/ig,'');
		str = str.replace(/<span style="color:#......;font-weight:bold">\d\d:\d\d ..: .{4,16} : afk<\/span><br>/ig,'');
		str = str.replace(/\d\d:\d\d ..: .{4,7} : back<br>/ig,'');
		str = str.replace(/<span style="color:#......;font-weight:bold">\d\d:\d\d ..: .{4,16} : back<\/span><br>/ig,'');
		
		return str
	}


	function parseDateLocalTime(strDate) {
		var reg = /^(\d{2})-(\d{2})-(\d{4}) (\d{2}):(\d{2})$/;
		var parts = reg.exec(strDate);
		return parts ? (new Date(parts[3], parts[1]-1, parts[2], parts[4], parts[5])) : null
	}
	
	function timeFromNowString(strPastTime) {
		var datNow = new Date();
		var datPastTime = parseDateLocalTime(strPastTime);
        var res = Math.abs((datNow.getTime() - datPastTime.getTime())/1000);
		var strOut = ''
			
        // get days
        var days = Math.floor(res / 86400);
 		
        // get hours        
        var hours = Math.floor(res / 3600) % 24;        
         
        // get minutes
        var minutes = Math.floor(res / 60) % 60;
		
		if (days > 0) {
			 strOut = days.toString() + 'd';
		} else if (hours > 0 ) {
			 strOut = hours.toString() + 'h';
		} else if (minutes > 0 ) {
			 strOut = minutes.toString() + 'm';
		}
		//console.log('Time: ' + strOut);
		return strOut;
	}
	
	socket.onmessage = function (message) {
		var datLastTimeReceived;
		var datCurTimeReceived;
		var intAudioTimeOut = 300000; // for audio tone. default of 5 minutes
		var textarea;
		var strTemp = "";
		var strOut = "";
		
		//console.log("Received: " + message.data.charCodeAt(0));
		//console.log("Received: " + message.data.substring(1,5));
		if (message.data.charCodeAt(0) == intDataCode) {
			if (message.data.substring(1,4) == "ini") {
				var strVars = message.data.substring(4);
				var objVars = JSON.parse(strVars);
				document.getElementById("lblInfoNode").innerHTML = objVars.NodeName;
				document.getElementById("lblInfoCall").innerHTML = objVars.CallSign;
				var x = document.getElementById("sel_port_list");
				x.options.length = 0; // clear hidden list
				document.getElementById("lblInfoPort1").innerHTML = objVars.Port1;
				if (objVars.Port1 != '') {
					var option = document.createElement("option");
					option.text = objVars.Port2;
					x.add(option);
				}
				document.getElementById("lblInfoPort2").innerHTML = objVars.Port2;
				if (objVars.Port2 != '') {
					var option = document.createElement("option");
					option.text = objVars.Port2;
					x.add(option);
				}
				document.getElementById("lblInfoPort3").innerHTML = objVars.Port3;
				if (objVars.Port3 != '') {
					var option = document.createElement("option");
					option.text = objVars.Port3;
					x.add(option);
				}
				document.getElementById("lblInfoPort4").innerHTML = objVars.Port4;
				if (objVars.Port4 != '') {
					var option = document.createElement("option");
					option.text = objVars.Port4;
					x.add(option);
				}
				if (objVars.Port5 != '') {
					var option = document.createElement("option");
					option.text = objVars.Port5;
					x.add(option);
				}
				if (objVars.Port6 != '') {
					var option = document.createElement("option");
					option.text = objVars.Port6;
					x.add(option);
				}
			} else if (message.data.substring(1,6) == "state") {
				// state flags
				var strVars = message.data.substring(6);
				var objVars = JSON.parse(strVars);
				if (objVars.ChatInSwitch == "0") {
					document.getElementById("btn_chat_power").checked = false;
					//document.getElementById("btn_chat_send").disabled = true;
					document.getElementById("btn_chat_join").disabled = true;
					document.getElementById("btn_chat_leave").disabled = true;
					document.getElementById("btn_chat_away").disabled = true;
					document.getElementById("btn_chat_return").disabled = true;
					document.getElementById("lblChatHead").innerHTML = "No Chatters";
					if (document.getElementById("chkShowHints").checked == true) {
						document.getElementById("lbl_chat_hint").innerHTML = "Hint: Make sure the SWITCH in upper right is on and click the Join button below.";
					}
					document.getElementById("txt_chat_status").innerHTML = "Chat switch is off<br>Click SWITCH<br>then Join below";
				} else if (objVars.ChatInSwitch == "1") {
					document.getElementById("btn_chat_power").checked = true;
					if (objVars.ChatJoined == "0") {
						document.getElementById("btn_chat_join").disabled = false;
						document.getElementById("btn_chat_leave").disabled = true;
						document.getElementById("btn_chat_away").disabled = true;
						document.getElementById("btn_chat_return").disabled = true;
						//document.getElementById("btn_chat_send").disabled = true;
						if (document.getElementById("chkShowHints").checked == true) {
							document.getElementById("lbl_chat_hint").innerHTML = "Hint: Click the Join button below to chat.";
						}
						document.getElementById("txt_chat_status").innerHTML = "Not in Chat<br>Click Join below";
						document.getElementById("lblChatHead").innerHTML = "No Chatters";
					} else if (objVars.ChatJoined == "1") {
						document.getElementById("btn_chat_join").disabled = true;
						document.getElementById("btn_chat_leave").disabled = false;
						document.getElementById("btn_chat_away").disabled = false;
						document.getElementById("btn_chat_return").disabled = true;
						//document.getElementById("btn_chat_send").disabled = false;
						document.getElementById("lbl_chat_hint").innerHTML = ""
					}
				}
				if (objVars.NodeInSwitch == "0") {
					document.getElementById("btn_node_power").checked = false;
					//document.getElementById("btn_node_send").disabled = true;
					if (document.getElementById("chkShowHints").checked == true) {
						document.getElementById("lbl_node_hint").innerHTML = "Hint: Make sure the SWITCH in upper right is on";
					}
				} else if (objVars.NodeInSwitch == "1") {
					document.getElementById("btn_node_power").checked = true;
					//document.getElementById("btn_node_send").disabled = false;
					document.getElementById("lbl_node_hint").innerHTML = ""
				}				
			} else if (message.data.substring(1,13) == "chat_history") {
				var strVars = message.data.substring(13);
				var objVars = JSON.parse(strVars);
				strTemp = objVars.ChatHistory;
				if (document.getElementById("chatSidebar").style.display == 'block') {
					strTemp = stripAwayBackFromText(strTemp);
				}

				if (document.getElementById("btn_chat_join").disabled == false) {
					strTemp = strTemp + "Click Join to enter Chat mode<br>";
				}
				textarea = document.getElementById("txt_chat");
				textarea.innerHTML = strTemp;

				// scroll to bottom
				textarea.scrollTop = textarea.scrollHeight;
			} 
			if (message.data.substring(1,10) == "chat_list") {
				var strVars = '{"chatters":' + message.data.substring(10) + "}";
				var objVars = JSON.parse(strVars);
				
				strOut = '<table cellpadding="0" cellspacing="0" style="width:100%;">';
				var intMax = objVars.chatters.length;
				for (var i = 0; i < intMax; i++) {
					var chatter = objVars.chatters[i];
					strName = chatter.Name;
					strTime = timeFromNowString(chatter.Time);
					
					strOut += '<tr>';
					//console.log(Date(chatter.Time * 1000));
					if (chatter.Status == 'AFK') {
						if (chatter.Call == document.getElementById("lblInfoCall").innerHTML) {
							document.getElementById("btn_chat_away").disabled = true;
							document.getElementById("btn_chat_return").disabled = false;
						}							
					}
					else if (chatter.Call == document.getElementById("lblInfoCall").innerHTML) {
						document.getElementById("btn_chat_away").disabled = false;
						document.getElementById("btn_chat_return").disabled = true;
					}
					strOut += '<td style="width:160px">';
					if (chatter.Status == 'AFK') {
						strOut += '<img id="chat_img' + i.toString() + '" src="static/reddot.png">';
					}
					else if (chatter.Status == 'ACT') {
						strOut += '<img id="chat_img' + i.toString() + '" src="static/greendot.png">';
						strTime = '';
					}
					else if (chatter.Status == 'UNK') {
						strOut += '<img id="chat_img' + i.toString() + '" src="static/blackdot.png">';
					}
					else {
						strOut += '<img id="chat_img' + i.toString() + '" src="static/greydot.png">';
					}										
					strOut += '<span style="color:' + chatter.Color + '">';
					strOut += chatter.Call + ', ' + strName + '</span>';
					strOut += '</td>';
					strOut += '<td style="text-align:right">';
					strOut += '<span style="color:#a9a9a9" id="chat_time' + i.toString() + '">' + strTime + '</span>';
					strOut += '</td></tr>';
				}
				strOut += '</table>';
				document.getElementById("txt_chat_status").innerHTML = strOut;
				document.getElementById("lblChatHead").innerHTML = intMax.toString() + ' Chatters'
				strOut = '&nbsp;';
				if (document.getElementById("chkShowHints").checked) {
					strOut = 'Status Hint:<br>'
					strOut += '<img src="static/greendot.png"> = Available<br>';
					strOut += '<img src="static/reddot.png"> = Away<br>';
					strOut += '<img src="static/greydot.png"> = Idle';
					//strOut += '<img src="static/blackdot.png"> = Unknown';
				}
				document.getElementById("txt_sidebar_hint").innerHTML = strOut;				
			} 
			else if (message.data.substring(1,12) == "chat_status") {
				var intColon = message.data.indexOf(':');
				var strIndex = message.data.substring(12,intColon);
				var strStatus = message.data.substring(intColon+1,intColon+4);
				var strTime = message.data.substring(intColon+4,);
				strTime = timeFromNowString(strTime);
				var strImage = '';
				if (strStatus == 'AFK') {
					strImage = 'static/reddot.png';
				}
				else if (strStatus == 'ACT') {
					strImage = 'static/greendot.png';
				}
				else if (strStatus == 'IDL') {
					strImage = 'static/greydot.png';
				}
				else if (strStatus == 'UNK') {
					strImage = 'static/blackdot.png';
				}
				$("#chat_img" + parseInt(strIndex)).attr('src',strImage);
				$("#chat_time" + parseInt(strIndex)).text(' ' + strTime);
			}
			else if (message.data.substring(1,8) == "options") {
				// passing in options
				var strVars = message.data.substring(8);
				var objVars = JSON.parse(strVars);

				document.getElementById("selChatSound").value = objVars.ChatAlertSound;
				document.getElementById("lblChatSoundBackup").innerHTML = objVars.ChatAlertSound;
				document.getElementById("lbl_chat_sound_file").innerHTML = objVars.ChatSoundFile;
				if (objVars.ChatSoundFile == 'Default') {
					chat_audio.setAttribute("src", "" );
					chat_audio.setAttribute('src', "static/tarpn_tone.mp3");
					chat_audio.setAttribute('src', "static/tarpn_tone.wav");
				}
				else {
					chat_audio.setAttribute("src", "" );
					chat_audio.setAttribute("src", "uploads/" + objVars.ChatSoundFile);
				}
				document.getElementById("lbl_chat_sound_file_backup").innerHTML = objVars.ChatSoundFile;
				document.getElementById("selChatVisual").value = objVars.ChatAlertVisual;
				document.getElementById("lblChatVisualBackup").innerHTML = objVars.ChatAlertVisual;
				document.getElementById("chkIgnoreJoins").value = objVars.IgnoreChatJoins;
				if (objVars.IgnoreChatJoins == 1) {
					document.getElementById("chkIgnoreJoins").checked = true;
				} else {
					document.getElementById("chkIgnoreJoins").checked = false;
				}
				document.getElementById("chkShowHints").value = objVars.ShowHints;
				if (objVars.ShowHints == 1) {
					document.getElementById("chkShowHints").checked = true;
				} else {
					document.getElementById("chkShowHints").checked = false;
				}
				document.getElementById("chkShowCommands").value = objVars.ShowCommands;
				if (objVars.ShowCommands == 1) {
					document.getElementById("chkShowCommands").checked = true;
				} else {
					document.getElementById("chkShowCommands").checked = false;
					document.getElementById("chat_commands_bar").style.display = "none";
					document.getElementById("node_commands_bar").style.display = "none";
					resizeDivs();
				}								
				document.getElementById("chkUseBBS").value = objVars.UseBBS;
				if (objVars.UseBBS == 1) {
					document.getElementById("chkUseBBS").checked = true;
					document.getElementById("btn_BBS").style.display = "block";
				} else {
					document.getElementById("chkUseBBS").checked = false;
					document.getElementById("btn_BBS").style.display = "none";
				}								
				document.getElementById("chkIgnoreBBSKilled").value = objVars.IgnoreBBSKilled;
				if (objVars.IgnoreBBSKilled == 1) {
					document.getElementById("chkIgnoreBBSKilled").checked = true;
				} else {
					document.getElementById("chkIgnoreBBSKilled").checked = false;
				}	
				document.getElementById("lbl_bbs_sound_file").innerHTML = objVars.BBSSoundFile;
				document.getElementById("lbl_bbs_sound_file_backup").innerHTML = objVars.BBSSoundFile;
				if (objVars.BBSSoundFile == 'Default') {
					bbs_audio.setAttribute("src", "" );
					bbs_audio.setAttribute('src', "static/tarpn_mail.mp3");
					bbs_audio.setAttribute('src', "static/tarpn_mail.wav");
				}
				else {
					bbs_audio.setAttribute("src", "" );
					bbs_audio.setAttribute("src", "uploads/" + objVars.BBSSoundFile);
				}
			}
			else if (message.data.substring(1,11) == 'mailcount>') {
				var intCount = message.data.substring(11,);
				if (intCount > 0) {
					var blPlaySound = false;
					if (intCount > document.getElementById("mail_count").innerHTML) {
						blPlaySound = true; 
					}
					if (document.getElementById("chk_mute").checked == true) {
						blPlaySound = false; // mute overrides all
					}
					if (blPlaySound) {
						// play a tone for new mail
						bbs_audio.play();
					}
					document.getElementById("mail_count").innerHTML = intCount;
					if (intCount == 1) {
						document.getElementById("mail_notify").innerHTML = document.getElementById("mail_notify").innerHTML.replace('Msgs','Msg');
					}
					else if (document.getElementById("mail_notify").innerHTML.indexOf('Msgs') == -1) {
						document.getElementById("mail_notify").innerHTML = document.getElementById("mail_notify").innerHTML.replace('Msg','Msgs');
					}	
					document.getElementById("mail_notify").style.display = "block";
				}
				else {
					document.getElementById("mail_notify").style.display = "none";
					document.getElementById("mail_count").innerHTML = "0";
				}
			}
			else if (message.data.substring(1,4) == '.^.') {
				// surprise!
				if (message.data.substring(4,6) == 'hi') {
					txt_node.empty();
				}
				else if (message.data.substring(4,7) == 'bye') {
					txt_node.empty();
				}
				else {
					txt_node.append(message.data.substring(4));
				}

				// scroll to bottom
				textarea = document.getElementById("txt_node");
				textarea.scrollTop = textarea.scrollHeight;					
			}
		}
		else if (message.data.charCodeAt(0) == intHiddenCode) {
			if (message.data.substring(1,9) == "bbs_list") {
				strBBS_list_JSON = '{"bbs_list":' + message.data.substring(9) + "}";
				//console.log (strBBS_list_JSON);
				var objVars = JSON.parse(strBBS_list_JSON);
				lst_BBS_msg = objVars.bbs_list;
				if ( $.fn.dataTable.isDataTable( '#bbs_msg_list' ) ) {
					BBS_table = $('#bbs_msg_list').DataTable();
					BBS_table.clear().rows.add(lst_BBS_msg).draw();
				}
				else {
					BBS_table = $('#bbs_msg_list').DataTable({
						data: lst_BBS_msg,
						"paging":   false,
						"ordering": false,
						"info":     false,
						"searching":false,
						"scrollY":	"300px",
						"scrollCollapse": true, 
						columns: [
							{ title: "Num", width: "40px" },
							{ title: "Date", width: "60px" },
							{ title: "Type", width: "60px" },
							{ title: "Status" , width: "100px"},
							{ title: "Length", width: "60px" },
							{ title: "To", width: "70px" },
							{ title: "At", width: "70px" },
							{ title: "From", width: "70px" },
							{ title: "Subject" }
						],
						"rowCallback": function(row, data) {
							if ((data[2] == 'Pers') && (data[3] == 'Not Read/Sent') && (data[5] == document.getElementById("lblInfoCall").innerHTML)) {
								$(row).css('background-color','#99ff9c');
							}
							else {
								$(row).css('background-color','');
							}
						}						
					});
				}	
				if (lst_BBS_msg.length > 0) {
					document.getElementById("txt_bbs_msg").innerHTML = 'Select a message from the list above to see the content.';
				}
				else {
					document.getElementById("txt_bbs_msg").innerHTML = 'There are no messages to show in the list above.';
				}
				document.getElementById("btn_bbs_delete").disabled = true;
				document.getElementById("btn_bbs_reply").disabled = true;
				document.getElementById("btn_bbs_fwd").disabled = true;
				//document.getElementById("btn_bbs_export").disabled = true;
			}
			else if (message.data.substring(1,8) == "bbs_msg") {
				document.getElementById("txt_bbs_msg").innerHTML = message.data.substring(8)
				var intKilled = -1;
				intKilled = message.data.substring(8).indexOf('Killed');
				var intHash = message.data.substring(8).indexOf('#');
				if ((intKilled > -1) && (intHash < intKilled) ){
					// set the table status to Killed
					strMsg = message.data.substring(8+intHash+1,8+intKilled-1);
					var intMax = lst_BBS_msg.length;
					for (var i = 0; i < intMax; i++) {
						if (lst_BBS_msg[i][0] == strMsg) {
							lst_BBS_msg[i][3] = 'Killed';
							document.getElementById("btn_bbs_delete").disabled = true;
							document.getElementById("btn_bbs_reply").disabled = true;
							document.getElementById("btn_bbs_fwd").disabled = true;
							//document.getElementById("btn_bbs_export").disabled = true;
							BBS_table.cell(i,3).data( 'Killed' ).draw();
							if (document.getElementById("chkIgnoreBBSKilled").checked == true) {
								document.getElementById("txt_bbs_msg").innerHTML = 'Refreshing the list of messages...';
								sendMessage({ data: HIDDEN_PREFIX + "bbs_refresh" });
							}
							break;
						}
					}
				}
				else {
					var intRead = message.data.substring(8).indexOf('Type/Status: PN');
					if (intRead > -1) {
						// set an unread message to read
						BBS_table.cell('.selected',3).data('Read').draw();
					} 
					document.getElementById("btn_bbs_delete").disabled = false;
					document.getElementById("btn_bbs_reply").disabled = false;
					document.getElementById("btn_bbs_fwd").disabled = false;
					//document.getElementById("btn_bbs_export").disabled = false;
				}
				$("#txt_bbs_msg").height(($("#BBS").height()-380));
			}
		}
		else if ((message.data.charCodeAt(0) == intChatCode) && 
				 (document.getElementById("chatSidebar").style.display == 'block') &&
			     ((message.data.substring(1).replace('</span>','').indexOf(' : away<br>') > -1) ||
			      (message.data.substring(1).replace('</span>','').indexOf(' : afk<br>') > -1) ||  
			      (message.data.substring(1).replace('</span>','').indexOf(' : back<br>') > -1)
			     )
			    ) {
				message.data = ''; // ignore the away message
		}
		else if (message.data.charCodeAt(0) == intChatCode) {
			// CHAT_PREFIX in first character denotes chat command
			datCurTimeReceived = new Date();
			datLastTimeReceived = new Date(
				parseInt(localStorage.getItem("lastTimeReceived"))
			);
			var intPlaySound = 0;
			var intShowVisual = 0;
			if (document.getElementById("selChatSound").value == 4) {
				intPlaySound = 1; // always beep
			}
			if (datCurTimeReceived - datLastTimeReceived > intAudioTimeOut) {
				if (document.getElementById("selChatSound").value >= 2) {
					intPlaySound = 1; // after inactivity
				}
				if (document.getElementById("selChatVisual").value >= 2) {
					intShowVisual = 1;
				}
				datLastTimeReceived = datCurTimeReceived; // reset timer
			} 
			else if (document.hasFocus() == false) {
				if (document.getElementById("selChatSound").value == 3) {
					intPlaySound = 1; // unfocused
				}
				if (document.getElementById("selChatVisual").value == 3) {
					intShowVisual = 1;
				}
			}
			if (document.getElementById("chkIgnoreJoins").checked == true &&
				(message.data.indexOf(": *** Left") > 0 ||
					message.data.indexOf("*** Joined Chat,") > 0)) {
				intPlaySound = 0;
				intShowVisual = 0;
			}
			if (message.data.indexOf(
					": " + document.getElementById("lblInfoCall").innerHTML) >= 0) {
				intPlaySound = 0; // don't play on my own message
				intShowVisual = 0;
			}
			if (document.getElementById("chk_mute").checked == true) {
				intPlaySound = 0; // mute overrides all
			}
			if (intPlaySound == 1) {
				// play a tone
				chat_audio.play();
			}
			if (intShowVisual == 1) {
				// highlight chat
				document.getElementById("btn_chat").className = 
					document.getElementById("btn_chat").className.replace("myMainColor", "w3-yellow");   
				document.getElementById("btn_chat").className = 
					document.getElementById("btn_chat").className.replace("w3-light-grey", "w3-yellow");   				
			}
			localStorage.setItem("lastTimeReceived", +new Date());
			if (message.data != '') {
				txt_chat.append(message.data.substring(1));
			}
			if (txt_chat.html().length >= 10000) {
				//remove from front if too long
				txt_chat.html(txt_chat.html().slice(txt_chat.html().length - 10000));
			}

			// scroll to bottom
			textarea = document.getElementById("txt_chat");
			textarea.scrollTop = textarea.scrollHeight;
			//} else if (message.data.substring(0,1) == ":") {
			//    // : denotes shell command
			//	shell_text.append(message.data.substring(1).replace(/\r\n|\r|\n/g,"<br>"));
			//	shell_text.append($('<br/>'));
		} else {
			// node window
			txt_node.append(message.data);

			if (txt_node.html().length >= 10000) {
				//remove from front if too long
				txt_node.html(txt_node.html().slice(txt_node.html().length - 10000));
			}

			// scroll to bottom
			textarea = document.getElementById("txt_node");
			textarea.scrollTop = textarea.scrollHeight;
		}
	};

	socket.onclose = function () {
		console.log("Disconnected");
	};

	var sendMessage = function (message) {
		localStorage.setItem("lastTimeReceived", +new Date()); //reset time since last receive
		//console.log("Sending:" + message.data);
		socket.send(message.data);
	};

	// GUI Stuff

	// send a node command to the serial port
	$("#btn_node_send").click(function (event) {
		event.preventDefault();
		sendNodeTextToNode();
	});

	// run after a CR
	$("#txt_node_send").submit(function (event) {
		event.preventDefault();
		sendNodeTextToNode();
	});

	function sendNodeTextToNode() {
		var cmd = $("#txt_node_send").val();
		// strip control chars
		cmd = cmd.replace(/[^\x20-\x7e]/g, '')

		if (cmd != "") {
			sendMessage({ data: cmd });
		}
		$("#txt_node_send").val("");

		// Add line to the Sent dropdown
		var selNodeSent = document.getElementById("sel_node_sent");
		var option = document.createElement("option");
		option.text = cmd;
		selNodeSent.add(option);
		selNodeSent.selectedIndex = selNodeSent.length - 1;
		if (selNodeSent.length == 1) {
			document.getElementById("lbl_last_node_sent").innerHTML =
				cmd + " (Up arrow to recall)";
		} else {
			document.getElementById("lbl_last_node_sent").innerHTML = cmd;
		}
	}

	$("#sel_node_sent").change(function () {
		$("#txt_node_send").val($(this).val());
	});

	$("#btn_node_clear").click(function (event) {
		event.preventDefault();
		txt_node.empty();
	});

	$("#btn_node_reconnect").click(function (event) {
		event.preventDefault();
		sendMessage({ data: NODE_PREFIX + "reconnect" });
	});

	$("#btn_open_sidebar").click(function (event) {
		event.preventDefault();
		document.getElementById("chatMiddle").style.marginRight = "220px";
		document.getElementById("chatSidebar").style.display = "block";
		document.getElementById("btn_open_sidebar").style.display = "none";
		localStorage.setItem("sidebar_open", "yes");
	});
	$("#btn_close_sidebar").click(function (event) {
		event.preventDefault();
		document.getElementById("chatMiddle").style.marginRight = "0%";
		document.getElementById("chatSidebar").style.display = "none";
		document.getElementById("btn_open_sidebar").style.display = "inline-block";
		localStorage.setItem("sidebar_open", "no");
	});

	// Node monitor checkbox clicked
	$("#chk_monitor").click(function (event) {
		// Get the checkbox
		var checkBox = document.getElementById("chk_monitor");

		// If the checkbox is checked, turn Monitor on
		if (checkBox.checked == true) {
			sendMessage({ data: DATA_PREFIX + "mon_on" });
		} else {
			sendMessage({ data: DATA_PREFIX + "mon_off" });
		}
	});

	$("#chk_mute").click(function (event) {
		// Get the checkbox
		var checkBox = document.getElementById("chk_mute");

		// If the checkbox is checked, turn sound off
		if (checkBox.checked == true) {
			localStorage.setItem("MuteChatFlag", 1);
		} else {
			localStorage.setItem("MuteChatFlag", 0);
		}
	});

	// send a chat command to the serial port
	$("#btn_chat_send").click(function (event) {
		event.preventDefault();
		sendChatTextToNode();
	});

	// run after a CR
	$("#txt_chat_send").submit(function (event) {
		event.preventDefault();
		sendChatTextToNode();
	});

	function sendChatTextToNode() {
		var cmd = $("#txt_chat_send").val();
		if (cmd != '') {
			// strip control characters
			cmd = cmd.replace(/[^\x20-\x7e]/g, '')

			if ((cmd == 'afk') || (cmd == 'away')) {
				document.getElementById("btn_chat_away").disabled = true;
				document.getElementById("btn_chat_return").disabled = false;
			}
			else if (document.getElementById("btn_chat_away").disabled) {
				document.getElementById("btn_chat_away").disabled = false;
				document.getElementById("btn_chat_return").disabled = true;
			}
			sendMessage({ data: CHAT_PREFIX + cmd });
			$("#txt_chat_send").val("");

			// Add line to the Sent dropdown
			var selChatSent = document.getElementById("sel_chat_sent");
			var option = document.createElement("option");
			option.text = cmd;
			selChatSent.add(option);
			selChatSent.selectedIndex = selChatSent.length - 1;

			if (selChatSent.length == 1) {
				document.getElementById("lbl_last_chat_sent").innerHTML =
					cmd + " (Up arrow to recall)";
			} else {
				document.getElementById("lbl_last_chat_sent").innerHTML = cmd;
			}
		}
	}

	$("#btn_chat_away").click(function (event) {
		event.preventDefault();
		document.getElementById("btn_chat_away").disabled = true;
		document.getElementById("btn_chat_return").disabled = false;
		sendMessage({ data: CHAT_PREFIX + "away" });
	});

	$("#btn_chat_return").click(function (event) {
		event.preventDefault();
		document.getElementById("btn_chat_away").disabled = false;
		document.getElementById("btn_chat_return").disabled = true;
		sendMessage({ data: CHAT_PREFIX + "back" });
	});
	
	// bbs stuff
    $('#bbs_msg_list tbody').on( 'click', 'tr', function () {
        if ( $(this).hasClass('selected') ) {
            $(this).removeClass('selected');
            document.getElementById("txt_bbs_msg").innerHTML = 'Click the list above to see the message'
            document.getElementById("btn_bbs_delete").disabled = true;
            //document.getElementById("btn_bbs_export").disabled = true;
            document.getElementById("btn_bbs_reply").disabled = true;
            document.getElementById("btn_bbs_fwd").disabled = true;
        }
        else {
            BBS_table.$('tr.selected').removeClass('selected');
            $(this).addClass('selected');
            document.getElementById("txt_bbs_msg").innerHTML = 'Reading message ' + BBS_table.cell('.selected',0).data() + '...';
            // read selected message
            sendMessage({ data: HIDDEN_PREFIX + "bbs_read_msg" + BBS_table.cell('.selected',0).data() });
        }
    } );
 
    $('#btn_bbs_delete').click( function () {
        document.getElementById("txt_bbs_msg").innerHTML = 'Killing message ' + BBS_table.cell('.selected',0).data();
        // Kill selected message
        sendMessage({ data: HIDDEN_PREFIX + "bbs_kill_msg" + BBS_table.cell('.selected',0).data() });
    } ); 
    $('#btn_bbs_refresh').click( function () {
        document.getElementById("txt_bbs_msg").innerHTML = 'Refreshing the list of messages...';
		sendMessage({ data: HIDDEN_PREFIX + "bbs_refresh" });
    } ); 
    
    $('#btn_bbs_reply').click( function () {
		document.getElementById("lbl_bbs_new_action").innerHTML = "Reply";
		// Hide the top fields
        document.getElementById("lbl_bbs_new_type").style.display='none';
        document.getElementById("sel_bbs_new_type").style.display='none';
		document.getElementById("txt_bbs_new_to").innerHTML = BBS_table.cell('.selected',7).data();
        document.getElementById("lbl_bbs_new_to").style.display='none';
        document.getElementById("txt_bbs_new_to").style.display='none';
        document.getElementById("lbl_bbs_new_subject").style.display='none';
        document.getElementById("txt_bbs_new_subject").style.display='none';
        document.getElementById("bbs_compose").style.display='block';
        $("#txt_bbs_new_text").focus();
    } ); 
    
    $('#btn_bbs_fwd').click( function () {
		document.getElementById("lbl_bbs_new_action").innerHTML = "Forward";
		//Hide the type and subject
        document.getElementById("lbl_bbs_new_type").style.display='none';
        document.getElementById("sel_bbs_new_type").style.display='none';
        document.getElementById("lbl_bbs_new_subject").style.display='none';
        document.getElementById("txt_bbs_new_subject").style.display='none';
        document.getElementById("bbs_compose").style.display='block';
        $("#txt_bbs_new_to").focus();
    } ); 
    
    $('#btn_bbs_compose').click( function () {
		document.getElementById("lbl_bbs_new_action").innerHTML = "New";
        document.getElementById("bbs_compose").style.display='block';
        $("#txt_bbs_new_to").focus();
    } ); 

	function reset_bbs_new() {
		document.getElementById("lbl_bbs_new_action").innerHTML = ""
		document.getElementById("txt_bbs_new_to").value = ""
		document.getElementById("txt_bbs_new_subject").value = ""
		document.getElementById("txt_bbs_new_text").value = ""
        document.getElementById("lbl_bbs_new_type").style.display='block';
        document.getElementById("sel_bbs_new_type").style.display='block';
 		document.getElementById("lbl_bbs_new_to").style.display='block';
        document.getElementById("txt_bbs_new_to").style.display='block';
        document.getElementById("lbl_bbs_new_subject").style.display='block';
        document.getElementById("txt_bbs_new_subject").style.display='block';
	}

	$("#btn_bbs_new_quit").click(function (event) {
		document.getElementById('bbs_compose').style.display='none';
		reset_bbs_new();
	});
	
	$("#btn_bbs_new_cancel").click(function (event) {
		document.getElementById('bbs_compose').style.display='none';
		reset_bbs_new();
	});     

	$("#btn_bbs_new_send").click(function (event) {
		var strInit = '';
		var strSubject =  '';
		if (document.getElementById("lbl_bbs_new_action").innerHTML == 'Reply') {
			strInit = 'SR ' + BBS_table.cell('.selected',0).data();
		}
		else if (document.getElementById("lbl_bbs_new_action").innerHTML == 'Forward') {
			strInit = 'SC ' + BBS_table.cell('.selected',0).data() + ' ' + document.getElementById("txt_bbs_new_to").value;
		}
		else {
			strInit = 'S' + document.getElementById("sel_bbs_new_type").value + ' ' + document.getElementById("txt_bbs_new_to").value;
			strSubject = document.getElementById("txt_bbs_new_subject").value;
		}
		var strMsg = document.getElementById("txt_bbs_new_text").value + '\r\n/ex\r\n';
		if (strMsg.length > 2000) {
			Alert('Message length is limited to 2000 characters. Please shorten your endless tome.');
		}
		else {
			// build JSON
			myObj = {
				InitStr: strInit,
				Subject: strSubject,
				Message: strMsg
			};
			var strJSON = JSON.stringify(myObj);
			//console.log(strJSON);
			sendMessage({ data: HIDDEN_PREFIX + "bbs_new_msg" + strJSON});		
			document.getElementById('bbs_compose').style.display='none';
			reset_bbs_new();
		}
	}); 	

	// sound stuff
	$("#btn_chat_sound_custom").on('click', function() {
		$('#chat_sound_file_input').trigger('click');
	});	 
	 
	// pick a sound file 
	$('#chat_sound_file_input').on('change', function(e) {
		var target = e.currentTarget;
		var file = target.files[0];
  
		if (target.files && file) {
			var reader = new FileReader();
			reader.onload = function (e) {
				var filename = $('#chat_sound_file_input').val().replace("C:\\fakepath\\", "");
				document.getElementById("lbl_chat_sound_file").innerHTML = filename;
				document.getElementById('lbl_chat_sound_bits').innerHTML = e.target.result;
			}
			reader.readAsDataURL(file);
		}
	});	

	$("#btn_chat_sound_default").on('click', function() {
		document.getElementById('lbl_chat_sound_bits').innerHTML = '';
		document.getElementById('lbl_chat_sound_file').innerHTML = 'Default';
	});
		
	$("#btn_chat_sound_play").on('click', function() {
		var temp_audio = document.createElement('audio');
		if (document.getElementById('lbl_chat_sound_bits').innerHTML == '') {
			if (document.getElementById("lbl_chat_sound_file").innerHTML == 'Default') {
				temp_audio.setAttribute('src', "static/tarpn_tone.mp3");
				temp_audio.setAttribute('src', "static/tarpn_tone.wav");
			}
			else {
				temp_audio.setAttribute('src', "uploads/" + document.getElementById("lbl_chat_sound_file").innerHTML);
			}
		}
		else {
			temp_audio.setAttribute('src', document.getElementById('lbl_chat_sound_bits').innerHTML);
		}
		temp_audio.play();
	});

	$("#btn_bbs_sound_custom").on('click', function() {
		$('#bbs_sound_file_input').trigger('click');
	});	 
	
	// pick a sound file 
	$('#bbs_sound_file_input').on('change', function(e) {
		var target = e.currentTarget;
		var file = target.files[0];
		var reader = new FileReader();
  
		if (target.files && file) {
			var reader = new FileReader();
			reader.onload = function (e) {
				document.getElementById('lbl_bbs_sound_bits').innerHTML = e.target.result;
				var filename = $('#bbs_sound_file_input').val().replace("C:\\fakepath\\", "");
				$('#lbl_bbs_sound_file').html(filename);
			}
			reader.readAsDataURL(file);
		}
	});	

	$("#btn_bbs_sound_default").on('click', function() {
		document.getElementById('lbl_bbs_sound_bits').innerHTML = '';
		document.getElementById('lbl_bbs_sound_file').innerHTML = 'Default';
	});
		
	$("#btn_bbs_sound_play").on('click', function() {
		var temp_audio = document.createElement('audio');
		if (document.getElementById('lbl_bbs_sound_bits').innerHTML == '') {
			if (document.getElementById("lbl_bbs_sound_file").innerHTML == 'Default') {
				temp_audio.setAttribute('src', "static/tarpn_mail.mp3");
				temp_audio.setAttribute('src', "static/tarpn_mail.wav");
			}
			else {
				temp_audio.setAttribute('src', "uploads/" + document.getElementById("lbl_bbs_sound_file").innerHTML);
			}
		}
		else {
			temp_audio.setAttribute('src', document.getElementById('lbl_bbs_sound_bits').innerHTML);
		}
		temp_audio.play();
	});

	// options stuff
	function cancelOptions() {
		document.getElementById("selChatSound").value = document.getElementById("lblChatSoundBackup").innerHTML;
		document.getElementById("selChatVisual").value = document.getElementById("lblChatVisualBackup").innerHTML;
		document.getElementById("lbl_chat_sound_file").innerHTML = document.getElementById("lbl_chat_sound_file_backup").innerHTML;
		document.getElementById("lbl_chat_sound_bits").innerHTML = '';
		document.getElementById("lbl_bbs_sound_file").innerHTML = document.getElementById("lbl_bbs_sound_file_backup").innerHTML;
		document.getElementById("lbl_bbs_sound_bits").innerHTML = '';
		if (document.getElementById("chkIgnoreJoins").value == 1) {
			document.getElementById("chkIgnoreJoins").checked = true;
		}
		else {
			document.getElementById("chkIgnoreJoins").checked = false;
		}	
		if (document.getElementById("chkShowHints").value == 1) {
			document.getElementById("chkShowHints").checked = true;
		}
		else {
			document.getElementById("chkShowHints").checked = false;
		}	
		if (document.getElementById("chkShowCommands").value == 1) {
			document.getElementById("chkShowCommands").checked = true;
		}
		else {
			document.getElementById("chkShowCommands").checked = false;
		}	
		if (document.getElementById("chkUseBBS").value == 1) {
			document.getElementById("chkUseBBS").checked = true;
		}
		else {
			document.getElementById("chkUseBBS").checked = false;
		}
		if (document.getElementById("chkIgnoreBBSKilled").value == 1) {
			document.getElementById("chkIgnoreBBSKilled").checked = true;
		}
		else {
			document.getElementById("chkIgnoreBBSKilled").checked = false;
		}		
		document.getElementById('options').style.display='none';
	} 

	$("#btn_quit_options").click(function (event) {
		cancelOptions();
	});
	
	$("#btn_cancel_options").click(function (event) {
		cancelOptions();
	});

//	function sleep(ms) {
//		return new Promise(resolve => setTimeout(resolve, ms));
//	}

	// sends a file from a form to the uploads directory
	function submit_file_form(form_to_send) {
		var formData = new FormData(form_to_send);	

		var xhr = new XMLHttpRequest();
		// Add any event handlers here...
		xhr.open('POST', form_to_send.getAttribute('action'), true);
		xhr.send(formData);
 
		xhr.onload = function() {
			if (xhr.status != 200) {
				// Reached the server, but it returned an error
				console.error('An error occurred uploading file');
			}   
		}

		xhr.onerror = function() {
			console.error('An error occurred uploading file ');
		};
		
		return false; // To avoid actual submission of the form
	}

	$("#btn_save_options").click(function (event) {
		var strOut;
		var intIgnoreJoins = 0;
		var intChatSound = document.getElementById("selChatSound").value;
		var intChatVisual = document.getElementById("selChatVisual").value;
		var intShowHints = 0;
		var intShowCommands = 0;
		var intUseBBS = 0;
		var intIgnoreBBSKilled = 0;

		event.preventDefault();
		if (document.getElementById("chkIgnoreJoins").checked == true) {
			intIgnoreJoins = 1;
		}
		if (document.getElementById("chkShowHints").checked == true) {
			intShowHints = 1;
		}
		if (document.getElementById("chkShowCommands").checked == true) {
			intShowCommands = 1;
			document.getElementById("chat_commands_bar").style.display = "block";
			document.getElementById("node_commands_bar").style.display = "block";
			resizeDivs();
		}
		else {
			document.getElementById("chat_commands_bar").style.display = "none";
			document.getElementById("node_commands_bar").style.display = "none";
			resizeDivs();
		}
		if (document.getElementById("chkUseBBS").checked == true) {
			intUseBBS = 1;
			document.getElementById("btn_BBS").style.display = "block";
		}
		else {
			if (document.getElementById("BBS").style.display == "block") {
				document.getElementById("BBS").style.display = "none";
				// show chat tab instead
				document.getElementById("btn_chat").className = document.getElementById("btn_chat").className.replace(" w3-light-grey", " myMainColor");
				document.getElementById("btn_BBS").className = document.getElementById("btn_BBS").className.replace(" myMainColor", " w3-light-grey");
				document.getElementById("Chat").style.display = "block";
			}
			document.getElementById("btn_BBS").style.display = "none";
		}		
		if (document.getElementById("chkIgnoreBBSKilled").checked == true) {
			intIgnoreBBSKilled = 1;
		}
		// save for later in case of cancel later
		document.getElementById("lblChatSoundBackup").innerHTML = document.getElementById("selChatSound").value;
		document.getElementById("lblChatVisualBackup").innerHTML = document.getElementById("selChatVisual").value;
		document.getElementById("chkIgnoreJoins").value = intIgnoreJoins;
		document.getElementById("chkShowHints").value = intShowHints;
		document.getElementById("chkShowCommands").value = intShowCommands;
		document.getElementById("chkUseBBS").value = intUseBBS;
		document.getElementById("chkIgnoreBBSKilled").value = intIgnoreBBSKilled;
		
		if (document.getElementById("lbl_chat_sound_file_backup").innerHTML != document.getElementById("lbl_chat_sound_file").innerHTML) {
			if ((document.getElementById("lbl_chat_sound_file").innerHTML != 'Default') &&
				(document.getElementById("lbl_chat_sound_bits").innerHTML != '')) {
				// send sound file to server;
				let sound_form = document.getElementById('frm_chat_sound_upload');
				submit_file_form(sound_form);
			}
			if (document.getElementById("lbl_chat_sound_file").innerHTML  == 'Default') {
				chat_audio.setAttribute("src", "" );
				chat_audio.setAttribute('src', "static/tarpn_tone.mp3");
				chat_audio.setAttribute('src', "static/tarpn_tone.wav");
			}
			else {
				chat_audio.setAttribute("src", "" );
				chat_audio.setAttribute("src", "uploads/" + document.getElementById("lbl_chat_sound_file").innerHTML);
			}			
			document.getElementById("lbl_chat_sound_file_backup").innerHTML = document.getElementById("lbl_chat_sound_file").innerHTML;
		}
		document.getElementById("lbl_chat_sound_bits").innerHTML = '';

		if (document.getElementById("lbl_bbs_sound_file_backup").innerHTML != document.getElementById("lbl_bbs_sound_file").innerHTML) {
			if ((document.getElementById("lbl_bbs_sound_file").innerHTML != 'Default') &&
				(document.getElementById("lbl_bbs_sound_bits").innerHTML != '')) {
				// send sound file to server;
				let sound_form = document.getElementById('frm_bbs_sound_upload');
				submit_file_form(sound_form);			
			}
			if (document.getElementById("lbl_bbs_sound_file").innerHTML  == 'Default') {
				bbs_audio.setAttribute("src", "" );
				bbs_audio.setAttribute('src', "static/tarpn_mail.mp3");
				bbs_audio.setAttribute('src', "static/tarpn_mail.wav");
			}
			else {
				bbs_audio.setAttribute("src", "" );
				bbs_audio.setAttribute("src", "uploads/" + document.getElementById("lbl_bbs_sound_file").innerHTML);
			}			
			document.getElementById("lbl_bbs_sound_file_backup").innerHTML = document.getElementById("lbl_bbs_sound_file").innerHTML;
		}
		document.getElementById("lbl_bbs_sound_bits").innerHTML = '';
		myObj = {
			ChatAlertSound: parseInt(document.getElementById("selChatSound").value),
			ChatSoundFile: document.getElementById("lbl_chat_sound_file").innerHTML,
			ChatAlertVisual: parseInt(document.getElementById("selChatVisual").value),
			IgnoreChatJoins: intIgnoreJoins,
			ShowHints: intShowHints,
			ShowCommands: intShowCommands,
			UseBBS: intUseBBS,
			IgnoreBBSKilled: intIgnoreBBSKilled,
			BBSSoundFile: document.getElementById("lbl_bbs_sound_file").innerHTML
		};
		strOut = JSON.stringify(myObj);
		sendMessage({ data: DATA_PREFIX + "options" + strOut });
		document.getElementById("options").style.display = "none";
	});

	document.onkeydown = function (e) {
		var blContinue = 0;
		if (document.activeElement == document.getElementById("txt_chat_send")) {
			var selSent = document.getElementById("sel_chat_sent");
			var txtSend = $("#txt_chat_send");
			blContinue = 1;
		} else if (
			document.activeElement == document.getElementById("txt_node_send")
		) {
			var selSent = document.getElementById("sel_node_sent");
			var txtSend = $("#txt_node_send");
			blContinue = 1;
		}
		if (blContinue == 1) {
			if (e.keyCode == "38") {
				//up arrow
				if (selSent.selectedIndex > -1) {
					if (txtSend.val() == "") {
						txtSend.val(selSent.value);
					} else if (
						txtSend.val() == selSent.value &&
						selSent.selectedIndex > 0
					) {
						selSent.selectedIndex = selSent.selectedIndex - 1;
						txtSend.val(selSent.value);
					}
				}
			} else if (e.keyCode == "40") {
				//down arrow
				if (selSent.selectedIndex > -1) {
					// dropdown not empty
					if (selSent.selectedIndex < selSent.length - 1) {
						if (txtSend.val() == "") {
							txtSend.val(selSent.value);
						} else if (txtSend.val() == selSent.value) {
							selSent.selectedIndex = selSent.selectedIndex + 1;
							txtSend.val(selSent.value);
						}
					}
				}
			}
		}
	};
	
	$("#btn_chat").click(function (event) {
		openTab('Chat');
	});
	$("#btn_node").click(function (event) {
		openTab('Node');
	});
	$("#btn_BBS").click(function (event) {
		openTab('BBS');
	});
	$("#btn_info").click(function (event) {
		openTab('Info');
	});

	function openTab(tabName) {
		var i, x, tablinks, textarea, myInput;
		var blWasOnBBS = false;
		// see if on BBS tab now
		if (document.getElementById('btn_BBS').className.indexOf('myMainColor') > -1) {
			blWasOnBBS = true;
		}
		x = document.getElementsByClassName("tarpnTab");
		for (i = 0; i < x.length; i++) {
			x[i].style.display = "none";  // hide all tabs
		}
		tablinks = document.getElementsByClassName("tablink");
		for (i = 0; i < x.length; i++) {
			tablinks[i].className = tablinks[i].className.replace(" myMainColor", " w3-light-grey");
		}
		document.getElementById(tabName).style.display = "block"; //show the current tab
		// scroll to bottom
		if (tabName == "Node") {
			textarea = document.getElementById('txt_node');
			myInput = document.getElementById('txt_node_send')
			document.getElementById('btn_node').className = document.getElementById('btn_node').className.replace(" w3-light-grey", " myMainColor");
			if (blWasOnBBS) {
				sendMessage({ data: HIDDEN_PREFIX + "bbs_exit" });
			}
			textarea.scrollTop = textarea.scrollHeight;
			myInput.focus();
		}
		else if (tabName == "Chat") {
			textarea = document.getElementById('txt_chat');
			myInput = document.getElementById('txt_chat_send')
			document.getElementById('btn_chat').className = document.getElementById('btn_chat').className.replace(" w3-light-grey", " myMainColor");
			if (blWasOnBBS) {
				sendMessage({ data: HIDDEN_PREFIX + "bbs_exit" });
			}
			textarea.scrollTop = textarea.scrollHeight;
			myInput.focus();
		}
		else if (tabName == "BBS") {
			textarea = document.getElementById('txt_bbs_msg');
			myInput = document.getElementById('txt_bbs_send')
			textarea.scrollTop = textarea.scrollHeight;
			document.getElementById('btn_BBS').className = document.getElementById('btn_BBS').className.replace(" w3-light-grey", " myMainColor");
			if (!blWasOnBBS) {
				document.getElementById("txt_bbs_msg").innerHTML = 'Reading the list of messages...'
				sendMessage({ data: HIDDEN_PREFIX + "bbs_enter" });
			}
		}
		else if (tabName == "Info") {
			//textarea = document.getElementById('txt_info');
			//myInput = document.getElementById('btn_info_refresh')
			document.getElementById('btn_info').className = document.getElementById('btn_info').className.replace(" w3-light-grey", " myMainColor");
			if (blWasOnBBS) {
				sendMessage({ data: HIDDEN_PREFIX + "bbs_exit" });
			}
			//textarea.scrollTop = textarea.scrollHeight;
		}
	}

	$("#btn_clear_logs").click(function (event) {
		sendMessage({ data: DATA_PREFIX + "clear_logs" });
		txt_chat.empty();
		txt_node.empty();
		alert('Logs cleared');
	});

	$("#sel_chat_sent").change(function () {
		$("#txt_chat_send").val($(this).val());
	});

	$("#btn_chat_clear").click(function (event) {
		event.preventDefault();
		txt_chat.empty();
	});

	$("#btn_chat_join").click(function (event) {
		event.preventDefault();
		sendMessage({ data: CHAT_PREFIX + "CHAT" });
		$("#txt_chat_send").focus();
	});

	$("#btn_chat_leave").click(function (event) {
		event.preventDefault();
		document.getElementById("txt_chat_status").innerHTML =
			"Not in Chat<br>Click Join below.";
		sendMessage({ data: CHAT_PREFIX + "/B" });
	});

	$("#sel_chat_cmds").change(function () {
		var sel_chat = document.getElementById("sel_chat_cmds")
		if (sel_chat.selectedIndex != 0) {
			var strCmd = $(this).val();
			$("#txt_chat_send").val(strCmd);
			if (strCmd.indexOf(' ') == -1) {
				// run a command if no spaces
				sendChatTextToNode();
			} 
			sel_chat.selectedIndex = 0;
		}
	});
	
	$("#sel_node_cmds").change(function () {
		var sel_node = document.getElementById("sel_node_cmds")
		if (sel_node.selectedIndex != 0) {
			var strCmd = $(this).val();
			$("#txt_node_send").val(strCmd);
			if (strCmd.indexOf(' ') == -1) {
				// run a command if no spaces
				sendNodeTextToNode();
			} 
			sel_node.selectedIndex = 0;
		}
	});

	$("#btn_chat_power").click(function (event) {
		if (document.getElementById("btn_chat_power").checked) {
			sendMessage({ data: CHAT_PREFIX + "connect" });
		} else {
			sendMessage({ data: CHAT_PREFIX + "disconnect" });
		}	
	});

	$("#btn_node_power").click(function (event) {
		if (document.getElementById("btn_node_power").checked) {
			sendMessage({ data: NODE_PREFIX + "connect" });
		} else {
			sendMessage({ data: NODE_PREFIX + "disconnect" });
		}	
	});
	
	$("#btnShutdown").click(function () {
		document.getElementById("btn_chat_power").checked = false;
		document.getElementById("btn_chat_send").disabled = true;
		document.getElementById("btn_chat_join").disabled = true;
		document.getElementById("btn_chat_leave").disabled = true;
		document.getElementById("lblChatHead").innerHTML = "No Chatters";
		document.getElementById("txt_chat_status").innerHTML =
			"Not in Chat<br>Click Join below.";
		sendMessage({ data: DATA_PREFIX + "shutdown" });
	});
});
