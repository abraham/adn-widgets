console.log('core.js:loaded');

var adnw = adnw || {};
adnw.init = function() {
  adnw.loadAssets();
  adnw.xdm();
  adnw.buildFollowButtons();
  $('body').on('click', '.adnw-follow', adnw.toggleFollow);    
};


adnw.buildFollowButtons = function(username) {
  if (username) {
    var $buttons = $('.adnw-unfollow[data-username="' + username + '"]');
    $buttons.addClass('adnw-btn-info').removeClass('adnw-unfollow');
    $buttons.text('Follow @' + username + ' on ADN');
  } else {
    $('.adnw-follow').addClass('adnw-btn adnw-btn-info')
  }
  // TODO: add titles to the buttons
};
adnw.buildUnfollowButtons = function(username) {
  var $buttons = $('.adnw-follow[data-username="' + username + '"]');
  $buttons.removeClass('adnw-btn-info').addClass('adnw-unfollow');
  $buttons.text('Unfollow @' + username + ' on ADN');
}


adnw.loadAssets = function() {
  $('head').append('<link href="' + adnw.host + '/style.css" rel="stylesheet">');
}

adnw.xdm = function() {
  adnw.socket = new easyXDM.Socket({
      remote: adnw.host + "/xdm.html",
      onMessage:function(message, origin) {
        message = JSON.parse(message);
        console.log('consumer:socket:onMessage:message', message);
        console.log('consumer:socket:onMessage:origin', origin);
        
        if (message.method === 'put' && message.action === 'expire') {
          localStorage.setItem('adnwExpire', message.data);
          adnw.expire = message.data
        } else if (message.method === 'post' && message.action === 'follow') {
          console.log('followed', message)
          adnw.buildUnfollowButtons(message.data);
        } else if (message.method === 'delete' && message.action === 'follow') {
          console.log('unfollowed', message)
          adnw.buildFollowButtons(message.data);
        }
      }
  });
}

adnw.postMessage = function(message) {
  adnw.socket.postMessage(JSON.stringify(message));
}

adnw.toggleFollow = function(event) {
  var $element = $(event.target);
  var username = $element.data('username');
  if (!username) {
    return;
  }
  var action = {
    'method': $element.hasClass('adnw-unfollow') ? 'delete' : 'put',
    'action': 'follow',
    'data': username
  }
  if (adnw.isExpired()) {
    console.log('authenticating profile');
    adnw.startAuthorization();
    // TODO: queue follow
    return false;
  }
  
  adnw.socket.postMessage(JSON.stringify(action));
  // TODO: preemptively change the button
  event.preventDefault();
}

adnw.startAuthorization = function() {
  adnw.childWindow = window.open(adnw.host + '/oauth/authenticate', 'adnwAuthentication', 'width=776,height=273');
}
adnw.completeAuthentication = function(profile) {
  console.log('completeAuthentication', profile);
}

adnw.isExpired = function() {
  var expire = adnw.expire || localStorage.getItem('adnwExpire');
  return !expire || parseInt(expire) < adnw.currentTime();
}
adnw.getProfile = function() {
  var profile = adnw.profile || localStorage.getItem('adnwprofile');
  if (!profile) {
    return false;
  }
  profile = JSON.parse(profile);
  if (profile.expire < adnw.currentTime()) {
    return false;
  }
  adnw.profile = profile;
  return profile;
}
adnw.setProfile = function(profile) {
  adnw.profile = profile;
  profile = JSON.stringify(profile);
  localStorage.getItem('adnwprofile', profile);
}
adnw.loadProfile = function(options) {
  $.get(adnw.host + '/api/profile', { access_token: options.accessToken }, function(profile, textStatus, jqXHR) {
    profile.access_token = options.accessToken;
    profile.expire = adnw.currentTime() + 3 * 60 * 60 * 1000;
    socket.postMessage(JSON.stringify({ 'method': 'put', 'action': 'expire', 'data': profile.expire }));
    options.callback(profile);
  });
}

adnw.followProfile = function(options) {
  $.post(adnw.host + '/api/follow', { access_token: options.accessToken, username: options.username }, function(profile, textStatus, jqXHR) {
    socket.postMessage(JSON.stringify({ 'method': 'post', 'action': 'follow', 'data': options.username }));
    if (options.callback) {
      options.callback(profile);
    }
  });
}
adnw.unfollowProfile = function(options) {
  $.ajax({
    type: "DELETE",
    url: adnw.host + '/api/follow',
    data: { access_token: options.accessToken, username: options.username },
    success: function(profile, textStatus, jqXHR) {
      socket.postMessage(JSON.stringify({ 'method': 'delete', 'action': 'follow', 'data': options.username }));
      if (options.callback) {
        options.callback(profile);
      }
    }
  });
  
  return;
  $.delete(adnw.host + '/api/follow', { access_token: options.accessToken, username: options.username }, function(profile, textStatus, jqXHR) {
    socket.postMessage(JSON.stringify({ 'method': 'delete', 'action': 'follow', 'data': options.username }));
    if (options.callback) {
      options.callback(profile);
    }
  });
}

adnw.currentTime = function() {
  return (new Date()).getTime();
}