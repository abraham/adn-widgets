console.log('provider:loaded');

var socket = new easyXDM.Socket({
  onMessage:function(message, origin) {
    message = JSON.parse(message);
    console.log('provider:socket:onMessage:message', message);
    console.log('provider:socket:onMessage:origin', origin);
    
    if (message.method === 'put' && message.action === 'follow') {
      adnw.followProfile({ username: message.data, accessToken: localStorage.getItem('adnwAccessToken') });
    } else if (message.method === 'delete' && message.action === 'follow') {
      adnw.unfollowProfile({ username: message.data, accessToken: localStorage.getItem('adnwAccessToken') });
    }
  }
});

$(window).on('storage', function (event) {
  console.log('provider:on:storage');
  var accessToken = localStorage.getItem('adnwAccessToken');
  if (accessToken) {
    adnw.loadProfile({ accessToken: accessToken, callback: adnw.completeAuthentication });
    // localStorage.removeItem('adnwAccessToken');
  }
});

var profile = adnw.getProfile();
if (profile) {
  console.log('sending expire');
  socket.postMessage(JSON.stringify({ 'method': 'put', 'action': 'expire', 'data': profile.expire }));
}