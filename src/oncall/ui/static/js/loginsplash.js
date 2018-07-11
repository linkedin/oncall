var oncallSplash = {
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
    this.events();
  },
  login: function(e){
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
    this.data.$loginForm.on('submit', this.login.bind(this));
  }

};

oncallSplash.init();
