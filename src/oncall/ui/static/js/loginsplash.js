var oncall = {
  data: {
    $loginForm: $('#login-form'),
    loginUrl: '/login',
    csrfKey: 'csrf-key'
  },
  callbacks: {
    onLogin: function (data){
      // callback for successful user login. Reloads page to go to the normal oncall interface.
      location.reload();
    }
  },
  init: function(){
    var self = this;
    this.events.call(this);

    $.ajaxSetup({
      cache: 'true'
    });
    $.ajaxPrefilter(function(options, originalOptions, jqXHR) {
      if (! options.crossDomain) {
        jqXHR.setRequestHeader('X-CSRF-TOKEN', localStorage.getItem(oncall.data.csrfKey));
      }
    });

    $(document).ajaxError(function(event, jqxhr){
      if (jqxhr.status === 401 && jqxhr.responseText && JSON.parse(jqxhr.responseText).title === 'Invalid Session') {
        self.logout.call(self);
        oncall.alerts.createAlert('Session Expired. Please login again.', 'danger');
      }
    });
  },
  login: function(e){
    console.log("in the form");
    e.preventDefault();
    var url = this.data.loginUrl,
        $form = this.data.$loginForm,
        self = this;

    $.ajax({
      url: url,
      type: 'POST',
      data: $form.serialize(),
      dataType: 'html'
    }).done(function(data){
      var data = JSON.parse(data),
          token = data.csrf_token;

      localStorage.setItem(self.data.csrfKey, token);

      
      self.callbacks.onLogin(data);
    }).fail(function(){
      alert('Invalid username or password.');
    });
  },
  events: function(){
    var self = this;
    
    this.data.$loginForm.on('submit', this.login.bind(this));
  }

};

oncall.init();
