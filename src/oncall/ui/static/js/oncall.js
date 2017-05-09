var router = new Navigo(root = null, useHash = false);

var oncall = {
  data: {
    $body: $('body'),
    $page: $('.content-wrapper'),
    $createBtn: $('#create-btn'),
    $userInfoContainer: $('.user-info-container'),
    $loginForm: $('#navbar-form'),
    $logoutBtn: $('.logout'),
    errorTemplate: $('#error-page-template').html(),
    loginUrl: '/login',
    logoutUrl: '/logout',
    user: $('body').attr('data-user'),
    userUrl: '/api/v0/users/',
    roles: [
      'primary',
      'secondary',
      'manager',
      'shadow',
      'vacation'
    ],
    modes: [
      'email',
      'sms',
      'call'
    ],
    timezones: [
      'US/Pacific',
      'US/Eastern',
      'US/Central',
      'US/Mountain',
      'US/Alaska',
      'US/Hawaii',
      'Asia/Kolkata',
      'UTC'
    ],
    userTimezone: null,
    userInfo: null,
    csrfKey: 'csrf-key',
    userInfoPromise: $.Deferred()
  },
  callbacks: {
    onLogin: function (data){
      // callback for successful user login. returns user info from API
    },
    onLogout: function (){
      // callback for successful user logout
    }
  },
  init: function(){
    var self = this;

    $.ajaxSetup({
      cache: 'true',
      headers: {'X-CSRF-TOKEN': localStorage.getItem(this.data.csrfKey)}
    });

    $(document).ajaxError(function(event, jqxhr, settings, thrownError){
      var error;
      if (jqxhr.status === 401 && jqxhr.responseText && JSON.parse(jqxhr.responseText).title === 'Invalid Session') {
        self.logout.call(self);
        oncall.alerts.createAlert('Session Expired. Please login again.', 'danger');
      }
    });

    this.defineRoutes();
    this.events.call(this);
    this.registerHandlebarHelpers();
    this.modal.init(this);
    this.multiSelect.init();
    if (this.data.user && this.data.user !== 'None') {
      this.getUserInfo().done(this.getUpcomingShifts.bind(this));
    } else {
      this.data.userInfoPromise.resolve();
    }
    Handlebars.registerPartial('error-page', this.data.errorTemplate);
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
      dataType: 'html',
    }).done(function(data){
      var data = JSON.parse(data),
          token = data.csrf_token;

      $.ajaxSetup({headers: {'X-CSRF-TOKEN': token}});
      localStorage.setItem(self.data.csrfKey, token);

      self.data.userInfo = data;
      self.data.user = data.name;
      self.data.userTimezone = data.time_zone;
      self.data.userInfoPromise.resolve();
      self.data.$body.attr('data-user', self.data.user).attr('data-authenticated', true);
      self.renderUserInfo.call(self, data);
      self.getUpcomingShifts();
      $form[0].reset();
      self.callbacks.onLogin(data);
    }).fail(function(data){
      oncall.alerts.createAlert('Invalid username or password.', 'danger');
    });
  },
  logout: function(){
    var url = this.data.logoutUrl,
        $container = this.data.$body.find('.user-info-container'),
        self = this;

    $.ajax({
      url: url,
      type: 'POST',
      dataType: 'html'
    }).done(function(){
      self.data.user = null;
      self.data.$body.attr('data-user', null).attr('data-authenticated', false);
      localStorage.removeItem(self.data.csrfKey);
      self.callbacks.onLogout();
    }).fail(function(){
      oncall.alerts.createAlert('Logout failed.', 'danger');
    });
  },
  getUserInfo: function(){
    var self = this;
    return $.get(this.data.userUrl + this.data.user).done(function(data){
      self.data.userInfo = data;
      self.data.user = data.name;
      self.data.userTimezone = data.time_zone;
      self.data.userInfoPromise.resolve();
      self.renderUserInfo.call(self, data);
    });
  },
  renderUserInfo: function(data){
    var $body = this.data.$body,
        $nav = $body.find('#navbar'),
        $container = $nav.find('.user-info-container');

    $body.attr('data-user', data.name);
    $nav.find('.user-dashboard-link').attr('href', '/dashboard/' + data.name);
    $container
      .find('.profile-picture').removeClass('placeholder').attr('src', data.photo_url)
      .end()
      .find('.user-settings-link').attr('href', '/user/' + data.name);
  },
  getUpcomingShifts: function(){
    var self = this,
        limit = 3; // Limit number of results

    $.get(this.data.userUrl + this.data.user + '/upcoming', { limit: limit }).done(function(data){
      self.renderUpcomingShifts.call(self, data);
    });
    // self.renderUpcomingShifts([{"end":1492369200,"num_events":0,"link_id":null,"start":1492282800,"schedule_id":2560,"role":"primary","user":"sebrahim","full_name":"Saif Ebrahim","team":"SaifTestTeam","id":259987},{"end":1493233200,"num_events":0,"link_id":null,"start":1492974000,"schedule_id":2548,"role":"primary","user":"sebrahim","full_name":"Saif Ebrahim","team":"SaifTestTeam","id":266854},{"end":1493578800,"num_events":0,"link_id":null,"start":1493492400,"schedule_id":2560,"role":"primary","user":"sebrahim","full_name":"Saif Ebrahim","team":"SaifTestTeam","id":266845}]);
  },
  renderUpcomingShifts: function(data){
    var $upcomingShifts = $('#upcoming-shifts');
        template = Handlebars.compile($('#upcoming-shifts-template').html());

    if (data.length) {
      $upcomingShifts.html(template(data));
      router.updatePageLinks();
    } else {
      $upcomingShifts.empty();
    }
  },
  events: function(){
    var self = this;
    $(document).ajaxSend(function(){
      self.data.$body.addClass('loading-view');
    });
    $(document).ajaxComplete(function(){
      self.data.$body.removeClass('loading-view');
    });
    this.data.$loginForm.on('submit', this.login.bind(this));
    this.data.$logoutBtn.on('click', this.logout.bind(this));
  },
  defineRoutes: function(){
    var self = this;
    router.on({
      'teams/all': function(){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.browse.init();
      },
      'team/:name/info': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.team.init(params.name, 'info');
        self.team.info.init(params.name);
      },
      'team/:name/schedules': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.team.init(params.name, 'schedules');
        self.team.schedules.init(params.name);
      },
      'team/:name': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.team.init(params.name, 'calendar');
        self.team.calendar.init(params.name);
      },
      'dashboard/:name': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.dashboard.init(params.name);
      },
      'user/:user/': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.settings.init();
      },
      'user/:user/notifications': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.settings.notifications.init();
      },
      'query/:query/:fields': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.data.$page.off(); //reset events on page init
        self.search.init(params);
      },
      '*': function(){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        window.history.replaceState({},'home', '/');
        self.search.init();
      }
    }).notFound(function(){
      router.navigate('/');
    });
    router.resolve();
  },
  recentlyViewed: {
    data: {
      storageKey: 'oncall-viewed-teams',
      maxLength: 6
    },
    setItem: function(name){
      var key = this.data.storageKey,
          itemList = JSON.parse(localStorage.getItem(key)) || [];

      if (itemList.indexOf(name) !== -1) {
        itemList.splice(itemList.indexOf(name), 1);
      }
      if (itemList.length === this.data.maxLength){
        itemList.pop();
      }
      itemList.unshift(name);
      localStorage.setItem(key, JSON.stringify(itemList));
    },
    getItems: function(){
      return JSON.parse(localStorage.getItem(this.data.storageKey));
    },
    replaceItem: function(oldItem, newItem){
      var key = this.data.storageKey,
          itemList = JSON.parse(localStorage.getItem(key));

      if (itemList.indexOf(oldItem) !== -1) {
        itemList[itemList.indexOf(oldItem)] = newItem;
      }

      localStorage.setItem(key, JSON.stringify(itemList));
    },
    deleteItem: function(name){
      var key = this.data.storageKey,
          itemList = JSON.parse(localStorage.getItem(key));

      itemList.splice(itemList.indexOf(name), 1);

    localStorage.setItem(key, JSON.stringify(itemList));
    }
  },
  browse: {
    data: {
      $page: $('.content-wrapper'),
      teamsUrl: '/api/v0/teams/',
      pageSource: $('#browse-teams-template').html(),
      browseCardTemplate: $('#browse-card-template').html()
    },
    init: function(name){
      Handlebars.registerPartial('browse-card', this.data.browseCardTemplate);
      this.getData();
    },
    events: function(){
      router.updatePageLinks();
    },
    getData: function(){
      $.get(this.data.teamsUrl, this.renderPage.bind(this));
    },
    renderPage: function(data){
      var template = Handlebars.compile(this.data.pageSource),
          data = data.sort(function(a,b){ return a.toLowerCase() > b.toLowerCase() ? 1 : -1 }),
          curLetter = null,
          dataArr = [];

      for (var i = 0; i < data.length; i++) {
        var cur = data[i],
            first = cur[0].toLowerCase();

        if (curLetter !== first) {
          curLetter = first;
          dataArr.push({key: first, items: [cur]});
        } else {
          dataArr[dataArr.length - 1].items.push(cur);
        }
      }

      this.data.$page.html(template(dataArr));
      this.events();
    }
  },
  dashboard: {
    data: {
      $page: $('.content-wrapper'),
      url: '/api/v0/users/',
      summaryUrl: '/api/v0/teams/',
      pageSource: $('#dashboard-template').html(),
      userDetails: '#user-details',
      cardColumnTemplate: $('#dashboard-card-column-template').html(),
      cardInnerTemplate: $('#dashboard-card-inner-template').html(),
      user: null
    },
    init: function(name){
      Handlebars.registerPartial('dashboard-card-inner', this.data.cardInnerTemplate);
      this.getData(this.data.user = name);
    },
    events: function(){
      router.updatePageLinks();
    },
    getData: function(name){
      var url = this.data.url + name,
          teamsUrl = url + '/teams',
          self = this,
          results = {
            user: name
          };

      $.get(teamsUrl, function(data){
        var pageModel = {
          data: data,
          name: name
        }
        self.renderPage.call(self, pageModel);
        $.get(url, self.renderUserDetails.bind(self));
        for (var i = 0; i < data.length; i++) {
          (function(i){
            var team = data[i],
                summaryUrl = self.data.summaryUrl + team + '/summary';
            $.get(summaryUrl, function(response){
              var model = {
                data: response,
                name: team
              }
              self.renderCardInner.call(self, model);
            });
          })(i);
        }
      }).fail(function(error){
        var data = {
          error: true,
          error_code: error.status,
          error_status: error.statusText,
          error_text: name + ' team not found'
        }
        self.renderPage(data);
      });
    },
    renderPage: function(data){
      var template = Handlebars.compile(this.data.pageSource);
      this.data.$page.html(template(data));
      this.events();
    },
    renderCardInner: function(data){
      var template = Handlebars.compile(this.data.cardInnerTemplate);
      this.data.$page.find('.dashboard-card[data-team="' + data.name + '"] .dashboard-card-inner').html(template(data));
      router.updatePageLinks();
    },
    renderUserDetails: function(data){
      var $el = this.data.$page.find(this.data.userDetails);
      $el.find('.headshot-large').attr('src', data.photo_url).removeClass('placeholder');
      $el.find('.user-details-name').text(data.full_name);
      $el.find('.user-details-email').html('<a href="mailto:' + data.contacts.email + '">' + data.contacts.email + '</a>');
    }
  },
  search: {
    data: {
      $page: $('.content-wrapper'),
      url: '/api/v0/search',
      summaryUrl: '/api/v0/teams/',
      pageSource: $('#search-template').html(),
      searchResultsSource: $('#search-results-template').html(),
      cardInnerTemplate: $('#recently-viewed-inner-template').html(),
      endpointTypes: ['services', 'teams'],
      searchForm: '.main-search',
      recentlyViewed: null
    },
    init: function(query){
      var $form,
          $input,
          typeaheadLimit = 10,
          services,
          teams,
          servicesCt,
          teamsCt,
          self = this;

      Handlebars.registerPartial('dashboard-card-inner', this.data.cardInnerTemplate);
      this.data.recentlyViewed = oncall.recentlyViewed.getItems();
      this.renderPage();
      this.getTeamSummaries();

      $form = this.data.$page.find(this.data.searchForm);
      $input = $form.find('.search-input');

      if (query) {
        this.getData.call(this, query);
        $form.find('.search-input').val(query.query);
      }

      services = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
          url: this.data.url + '?keyword=%QUERY',
          rateLimitWait: 200,
          wildcard: '%QUERY',
          transform: function(resp){
            var newResp = [],
                keys = Object.keys(resp.services);

            servicesCt = keys.length;
            for (var i = 0, item; i < keys.length; i++) {
              newResp.push({
                team: resp.services[keys[i]],
                service: keys[i]
              });
            }

            return newResp;
          }
        }
      });
      teams = new Bloodhound({
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
          url: this.data.url + '?keyword=%QUERY',
          rateLimitWait: 200,
          wildcard: '%QUERY',
          transform: function(resp){
            teamsCt = resp.teams.length;
            return resp.teams;
          }
        }
      });

      $input.typeahead(null, {
        name: 'teams',
        hint: true,
        async: true,
        highlight: true,
        limit: typeaheadLimit,
        source: teams,
        templates: {
          header: function(resp){
            return '<h4> Teams </h4>';
          },
          suggestion: function(resp){
            return '<div><a href="/team/' + resp + '" data-navigo>' + resp + '</a></div>';
          },
          footer: function(resp){
            if (teamsCt > typeaheadLimit) {
              return '<div class="tt-see-all"><a href="/query/' + resp.query + '/teams" data-navigo> See all ' + teamsCt + ' results for teams »</a></div>';
            }
          },
          empty: function(resp){
            return '<h4> No results found for "' + resp.query + '" </h4>';
          }
        }
      },
      {
        name: 'services',
        hint: true,
        async: true,
        highlight: true,
        limit: typeaheadLimit,
        displayKey: 'team',
        source: services,
        templates: {
          header: function(resp){
            return '<h4> Services </h4>';
          },
          suggestion: function(resp){
            return '<div><a href="/team/' + resp.team + '" data-navigo>' + resp.service + ' - ' + '<i>' + resp.team + '</i></a></div>';
          },
          footer: function(resp){
            if (servicesCt > typeaheadLimit) {
              return '<div class="tt-see-all"><a href="/query/' + resp.query + '/services" data-navigo> See all ' + servicesCt + ' results for services »</a></div>';
            }
          }
        }
      });

      $input
      .on('typeahead:asyncrequest', function(){
        $input.parents(self.data.searchForm).addClass('loading');
      })
      .on('typeahead:asyncreceive', function(){
        $input.parents(self.data.searchForm).removeClass('loading');
      })
      .on('typeahead:asynccancel', function(){
        $input.parents(self.data.searchForm).removeClass('loading');
      })
      .on('typeahead:render', function(){
        router.updatePageLinks();
      })
      .on('typeahead:selected', function(e, item){
        router.navigate('/team/' + $(this).val());
      });
    },
    events: function(){
      this.data.$page.on('submit', this.data.searchForm, this.updateSearch.bind(this));
      router.updatePageLinks();
    },
    getData: function(query) {
      var self = this,
          param = {
            keyword: query.query
          };
      if (query.fields !== "all") {
        param.fields = query.fields;
      }

      $.get(this.data.url, param, this.renderResults.bind(this));
    },
    getTeamSummaries: function(){
      var data = this.data.recentlyViewed,
          self = this;
      if (data) {
        for (var i = 0; i < data.length; i++) {
          (function(i){
            var team = data[i],
                summaryUrl = self.data.summaryUrl + team + '/summary';
            $.get(summaryUrl).done(function(response){
              var model = {
                data: response,
                name: team
              }
              self.renderCardInner.call(self, model);
            }).fail(function(response){
              var model = {
                data: response,
                name: team
              }
              self.renderCardInner.call(self, model);
            });
          })(i);
        }
      }
    },
    renderPage: function(){
      var template = Handlebars.compile(this.data.pageSource);
      this.data.$page.html(template(this.data.recentlyViewed));
      this.events();
    },
    renderCardInner: function(data){
      var template = Handlebars.compile(this.data.cardInnerTemplate);
      this.data.$page.find('.dashboard-card[data-team="' + data.name + '"] .dashboard-card-inner').html(template(data));
      router.updatePageLinks();
    },
    updateSearch: function(e){
      e.preventDefault();
      var $form = $(e.target),
          fields = 'all',
          query = $form.find('.tt-input').val();

      query = query + '/' + fields;
      router.navigate('/query/' + query);
    },
    renderResults: function(data){
      var template = Handlebars.compile(this.data.searchResultsSource);
      if (data.services && data.teams && Object.keys(data.services).length === 0 && data.teams.length === 0) {
        // Mark object empty if not search results are returned
        data.noResults = true;
      }

      this.data.$page.find('.search-results').html(template(data));
      router.updatePageLinks();
    }
  },
  team: {
    data: {
      $page: $('.content-wrapper'),
      url: '/api/v0/teams/',
      teamSubheaderTemplate: $('#team-subheader-template').html(),
      subheaderWrapper: '.subheader-wrapper',
      deleteTeam: '#delete-team',
      teamName: null,
      route: null
    },
    init: function(name, route){
      Handlebars.registerPartial('team-subheader', this.data.teamSubheaderTemplate);
      this.data.$page.off(); //reset events on page init
      this.data.teamName = decodeURIComponent(name);
      this.data.route = route;
    },
    createTeam: function($modal, $caller, $form) {
      var self = this,
          url = this.data.url,
          $modalBody = $modal.find('.modal-body'),
          $cta = $modal.find('.modal-cta'),
          name = $form.find('#team-name').val(),
          email = $form.find('#team-email').val(),
          slack = $form.find('#team-slack').val(),
          timezone = $form.find('#team-timezone').val(),
          model = {};

      $form.find(':input[type="text"]').each(function(){
        var $this = $(this);
        if ($this.val().length) {
          model[$this.attr('name')] = $this.val();
        }
      });
      model[$form.find('#team-timezone').attr('name')] = timezone;

      $cta.addClass('loading disabled').prop('disabled', true);
      $.ajax({
        type: 'POST',
        url: url,
        contentType: 'application/json',
        dataType: 'html',
        data: JSON.stringify(model)
      }).done(function(){
        $modal.modal('hide');
        router.navigate('/team/' + name + '/info');
      }).fail(function(data){
        var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || data.statusText;
        oncall.alerts.createAlert('Failed: ' + error, 'danger', $modalBody);
      }).always(function(){
        $cta.removeClass('loading disabled').prop('disabled', false);
      });
    },
    updateTeamName: function($modal, $caller, $form){
      var self = this,
          url = this.data.url + this.data.teamName,
          $modalBody = $modal.find('.modal-body'),
          $cta = $modal.find('.modal-cta'),
          name = $form.find('#team-name').val(),
          email = $form.find('#team-email').val(),
          slack = $form.find('#team-slack').val(),
          timezone = $form.find('#team-timezone').val(),
          model = {};

      $form.find(':input[type="text"]').each(function(){
        var $this = $(this);
        if ($this.val().length) {
          model[$this.attr('name')] = $this.val();
        }
      });
      model[$form.find('#team-timezone').attr('name')] = timezone;

      $cta.addClass('loading disabled').prop('disabled', true);
      $.ajax({
        type: 'PUT',
        url: url,
        dataType: 'html',
        contentType: 'application/json',
        data: JSON.stringify(model)
      }).done(function(){
        var template = Handlebars.compile(self.data.teamSubheaderTemplate),
            blankModel = {
              name: name,
              email: email,
              slack_channel: slack,
              scheduling_timezone: timezone,
              page: self.data.route
            },
            state = (self.data.route === 'calendar') ? name : '/team/' + name + '/' + self.data.route;

        $modal.modal('hide');
        $caller.attr('data-modal-val', name).find('span').text(name);
        window.history.replaceState({}, name, state); // Push new team name to location bar for reload/linking
        oncall.recentlyViewed.replaceItem(self.data.teamName, name);
        self.data.teamName = name;
        self[self.data.route].data.teamName = name;
        self.data.$page.find(self.data.subheaderWrapper).html(template(blankModel));
        router.updatePageLinks();
      }).fail(function(data){
        var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Update failed.';
        oncall.alerts.createAlert(error, 'danger', $modalBody);
      }).always(function(){
        $cta.removeClass('loading disabled').prop('disabled', false);
      });
    },
    deleteTeam: function($modal, $caller){
      var $card = $caller.parents('.module-card'),
          $modalBody = $modal.find('.modal-body'),
          $cta = $modal.find('.modal-cta'),
          url = this.data.url + this.data.teamName,
          self = this;

      $cta.addClass('loading disabled').prop('disabled', true);

      $.ajax({
        type: 'DELETE',
        url: url,
        dataType: 'html'
      }).done(function(e){
        $modal.modal('hide');
        oncall.recentlyViewed.deleteItem(self.data.teamName);
        router.navigate('/');
      }).fail(function(data){
        var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
        oncall.alerts.createAlert(error, 'danger', $modalBody);
      }).always(function(){
        $cta.removeClass('loading disabled').prop('disabled', false);
      });
    },
    calendar: {
      data: {
        $page: $('.content-wrapper'),
        calendar: '#calendar-container',
        $calendar: null,
        url: '/api/v0/teams/',
        pageSource: $('#team-calendar-template').html(),
        cardColumnTemplate: $('#card-column-template').html(),
        cardInnerTemplate: $('#card-inner-slim-template').html(),
        cardOncallTemplate: $('#card-oncall-template').html(),
        addCardTemplate: $('#add-card-item-template').html(),
        calendarTypesTemplate: $('#calendar-types-template').html(),
        cardExtra: '.card-inner[data-collapsed]',
        cardExtraChevron: '.card-inner[data-collapsed] .svg-icon-chevron',
        timezoneDisplay: '.timezone-display',
        teamName: null,
        teamData: null
      },
      init: function(name){
        var self = this;

        Handlebars.registerPartial('card-inner-slim', this.data.cardInnerTemplate);
        Handlebars.registerPartial('card-oncall', this.data.cardOncallTemplate);
        this.data.$page.off();
        this.data.teamName = decodeURIComponent(name);
        this.getData(name);
        oncall.callbacks.onLogin = function(){
          self.init(name);
        }
        oncall.callbacks.onLogout = function(){
          self.checkIfAdmin();
          self.data.$calendar.incalendar('updateCalendarOption', 'user', null);
          self.data.$calendar.incalendar('updateCalendarOption', 'readOnly', true, true);
        }
      },
      events: function(){
        this.data.$page.on('click', this.data.cardExtraChevron, this.toggleCardExtra.bind(this));
        router.updatePageLinks();
      },
      getData: function(name){
        var self = this;
        $.getJSON(this.data.url + this.data.teamName).done(function(data){
          self.data.teamData = data;
          self.renderPage(data);
          self.getTeamSummary();
          self.checkIfAdmin();
          oncall.recentlyViewed.setItem(self.data.teamName);
        }).fail(function(error){
          var data = {
            error: true,
            error_code: error.status,
            error_status: error.statusText,
            error_text: name + ' team not found'
          }
          self.renderPage(data);
        });
      },
      getTeamSummary: function(){
        var self = this;
        $.getJSON(this.data.url + this.data.teamName + '/summary', this.renderTeamSummary.bind(this));
      },
      renderPage: function(data){
        var template = Handlebars.compile(this.data.pageSource),
            self = this;

        self.data.$page.html(template(data));
        self.events();
        self.data.$calendar = $(self.data.calendar);
        // wait for user info data before creating calendar for timezone reasons
        oncall.data.userInfoPromise.done(function(){
          $(self.data.timezoneDisplay).text(oncall.data.userTimezone || 'System time');

          self.data.$calendar.incalendar(
            {
              eventsUrl: '/api/v0/events',
              getEventsUrl: '/api/v0/events?team__eq=' + self.data.teamName,
              onInit: self.renderCalendarTypes.bind(self),
              onAddEvents: function (events) {
                for (var i = 0; i < events.length; i++) {
                  var evt = events[i],
                      userData = self.data.teamData.users[evt.user];
                  // #TODO: Fix after full name from API is sorted out. in the mean time, replaces the username of the event with full name for display.
                  if (!evt.full_name && userData.full_name) {
                    evt.full_name = userData.full_name;
                    self.data.$calendar.find('.inc-event[data-id="' + evt.id + '"]').find('.inc-event-name').text(userData.full_name);
                  }
                }
              },
              onEventMouseover: function($el, evt){
                self.data.$calendar.find('[data-id="' + evt.id + '"]').attr('data-highlighted', true);
              },
              onEventMouseout: function($el, evt){
                if ($el.attr('data-modal-open') !== 'true') {
                  self.data.$calendar.find('[data-id="' + evt.id + '"]').attr('data-highlighted', false);
                }
              },
              onModalOpen: function($modal){
                if ($modal.hasClass('inc-create-event-modal')) {
                  oncall.typeahead.init(null, function(){$modal.find('#inc-role').trigger('change')}, self.data.teamName);
                } else {
                  oncall.typeahead.init(null, null, self.data.teamName);
                }
              },
              onEventDetailsModalOpen: function($modal, $calendar, $eventItem, evt){
                $eventItem.attr('data-modal-open', true);
                self.renderEventUserDetails($modal, $calendar, $eventItem, evt);
              },
              onEventDetailsModalClose: function($modal, $calendar){
                var evtId = $modal.attr('data-event-id');
                self.data.$calendar.find('[data-id="' + evtId + '"]').attr('data-modal-open', false);
              },
              user: oncall.data.user,
              readOnly: oncall.data.user ? false : true,
              timezone: oncall.data.userTimezone,
              team: self.data.teamName,
              roles: oncall.data.roles
            }
          )
        });

      },
      checkIfAdmin: function(){
        var data = this.data.teamData;

        data.isAdmin = false;

        for (var i in data.admins) {
          if (data.admins[i].name === oncall.data.user) {
            data.isAdmin = true;
          }
        }

        this.data.$page.attr('data-admin', data.isAdmin);
      },
      renderTeamSummary: function(data){
        var template = Handlebars.compile(this.data.cardOncallTemplate),
            $container = this.data.$page.find('#oncall-now-container');

        $container.html(template(data));
      },
      renderCalendarTypes: function(incalendar){
        var template = Handlebars.compile(this.data.calendarTypesTemplate),
            $container = this.data.$page.find('#calendar-types-container'),
            rolesModel = {
              roles: oncall.data.roles,
              currentViewRoles: incalendar.getCalendarOption('currentViewRoles')
            },
            self = this;

        $container
        .html(template(rolesModel))
        .on('change', '.calendar-types input[type="checkbox"]', function(){
          var type = $(this).attr('data-type'),
              action = $(this).prop('checked') ? 'show' : 'hide',
              activeTypesArray = [];

          $(this).parents('.calendar-types').find('input[type="checkbox"]:checked').each(function(){
            activeTypesArray.push($(this).val());
          });

          self.data.$calendar.incalendar('updateDisplayedEvents', activeTypesArray);
        });

      },
      toggleCardExtra: function(e){
        var $this = $(e.target),
            $card = $this.parents(this.data.cardExtra);

        $card.attr('data-collapsed', $card.attr('data-collapsed') === "true" ? false : true);
      },
      renderEventUserDetails: function($modal, $calendar, $eventItem, evt) {
        // #TODO: Leverage this to create whole modal
        var $ul = $modal.find('.inc-event-details-view'),
            $title = $modal.find('.inc-event-details-title'),
            userData = this.data.teamData.users[evt.user];

        $title.text(userData.full_name);
        $ul
        .append(
          $('<li />')
          .append('<label class="label-col">E-Mail</label>')
          .append('<span class="data-col"><a href="mailto:' + userData.contacts.email + '" target="_blank">' + userData.contacts.email + '</a></span>')
        )
        .append(
          $('<li />')
          .append('<label class="label-col">Call</label>')
          .append('<span class="data-col"><a href="tel:' + userData.contacts.call + '">' + userData.contacts.call + '</a></span>')
        )
        .append(
          $('<li />')
          .append('<label class="label-col">SMS</label>')
          .append('<span class="data-col"><a href="tel:' + userData.contacts.sms + '">' + userData.contacts.sms + '</a></span>')
        )
        .append(
          $('<li />')
          .append('<label class="label-col">Slack</label>')
          .append('<span class="data-col">' + userData.contacts.im + '</span>')
        )
      }
    },
    info: {
      data: {
        $page: $('.content-wrapper'),
        url: '/api/v0/teams/',
        pageSource: $('#team-info-template').html(),
        cardColumnTemplate: $('#card-column-template').html(),
        cardInnerTemplate: $('#card-inner-template').html(),
        addCardTemplate: $('#add-card-item-template').html(),
        serviceItemTemplate: $('#service-item-template').html(),
        editCardHeading: '.edit-card-heading',
        removeRoster: '.remove-card-column',
        addCardItem: '.add-card-item',
        addItemForm: '.add-item-form',
        cancelCardItem: '.cancel-card-item',
        toggleRotation: '.toggle-rotation',
        teamName: null,
        teamData: null
      },
      init: function(name){
        var self = this;

        this.data.teamName = decodeURIComponent(name);
        Handlebars.registerPartial('card-column', this.data.cardColumnTemplate);
        Handlebars.registerPartial('card-inner', this.data.cardInnerTemplate);
        Handlebars.registerPartial('add-card-item', this.data.addCardTemplate);
        Handlebars.registerPartial('service-item', this.data.serviceItemTemplate);
        if (name === 'create') {
          this.renderPage();
        } else {
          this.getData(name);
        }
        oncall.callbacks.onLogin = function(){
          self.checkIfAdmin();
        }
        oncall.callbacks.onLogout = function(){
          self.checkIfAdmin();
        }
      },
      events: function(){
        var data = this.data;
        data.$page.on('click', data.addCardItem + ',' + data.cancelCardItem, this.toggleAddItem);
        data.$page.on('submit', data.addItemForm, this.addCardItem.bind(this));
        data.$page.on('click', data.toggleRotation, this.toggleRotation.bind(this));
        router.updatePageLinks();
      },
      getData: function(name){
        var self = this;
        $.getJSON(this.data.url + this.data.teamName).done(function(data){
          self.data.teamData = data;
          self.renderPage(data);
          self.checkIfAdmin();
          oncall.recentlyViewed.setItem(self.data.teamName);
        }).fail(function(error){
          var data = {
            error: true,
            error_code: error.status,
            error_status: error.statusText,
            error_text: name + ' team not found'
          }
          self.renderPage(data);
        });
      },
      renderPage: function(data){
        var template = Handlebars.compile(this.data.pageSource);
        this.data.$page.html(template(data));
        this.events();
        oncall.typeahead.init();
      },
      checkIfAdmin: function(){
        var data = this.data.teamData;

        data.isAdmin = false;

        for (var i in data.admins) {
          if (data.admins[i].name === oncall.data.user) {
            data.isAdmin = true;
          }
        }

        this.data.$page.attr('data-admin', data.isAdmin);
      },
      toggleAddItem: function(){
        var $wrapper = $(this).parents('.add-item-wrapper'),
            $form = $wrapper.find('.add-item-form'),
            $input = $form.find('.add-item-name.tt-input'),
            $errorTxt = $form.find('.error-text');

        $wrapper.attr('data-view', function(){
          if ($wrapper.attr('data-view') === 'button') {
            $wrapper.attr('data-view', 'form');
            $input.typeahead('val','').trigger('focus');
          } else {
            $wrapper.attr('data-view', 'button');
            $errorTxt.empty();
          }
        });
      },
      updateRosterName: function($modal, $caller, name){
        var $card = $caller.parents('.module-card'),
            $modalBody = $modal.find('.modal-body'),
            $cta = $modal.find('.modal-cta'),
            roster = $card.attr('data-col-name'),
            url = this.data.url + this.data.teamName + '/rosters/' + roster;

        $cta.addClass('loading disabled').prop('disabled', true);

        $.ajax({
          type: 'PUT',
          url: url,
          dataType: 'html',
          contentType: 'application/json',
          data: JSON.stringify({name: name})
        }).done(function(){
          $modal.modal('hide');
          $caller.attr('data-modal-val', name).siblings('span.card-heading').text(name);
          $card.attr('data-col-name', name);
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Update failed.';
          oncall.alerts.createAlert('Update: ' + error, 'danger', $modalBody);
        }).always(function(){
          $cta.removeClass('loading disabled').prop('disabled', false);
        });
      },
      addRoster: function($modal, $caller, cardName){
        var self = this,
            emptyCard = { name: cardName },
            template = Handlebars.compile(this.data.cardColumnTemplate),
            url = this.data.url + this.data.teamName + '/rosters/',
            $modalBody = $modal.find('.modal-body'),
            $modalInput = $modal.find('input[type="text"]'),
            $cta = $modal.find('#create-item');

        $cta.addClass('loading disabled').prop('disabled', true);

        $.ajax({
          type: 'POST',
          url: url,
          contentType: 'application/json',
          dataType: 'html',
          data: JSON.stringify({name: cardName})
        }).done(function(){
          self.data.$page.find('.card-wrap').prepend(template(emptyCard));
          $modal.modal('hide');
          oncall.typeahead.init();
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Failed to add roster.';
          oncall.alerts.createAlert('Failed: ' + error, 'danger', $modalBody);
          $modalInput.trigger('focus');
        }).always(function(){
          $cta.removeClass('loading disabled').prop('disabled', false);
        });
      },
      removeRoster: function($modal, $caller){
        var $card = $caller.parents('.module-card'),
            $column = $card.parents('.card-column'),
            $modalBody = $modal.find('.modal-body'),
            $cta = $modal.find('.modal-cta'),
            roster = $card.attr('data-col-name'),
            url = this.data.url + this.data.teamName + '/rosters/' + roster;

        $cta.addClass('loading disabled').prop('disabled', true);

        $.ajax({
          type: 'DELETE',
          url: url,
          dataType: 'html'
        }).done(function(e){
          $modal.modal('hide');
          $column.remove();
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
          oncall.alerts.createAlert(error, 'danger', $modalBody);
        }).always(function(){
          $cta.removeClass('loading disabled').prop('disabled', false);
        });
      },
      addCardItem: function(e){
        e.preventDefault();
        var $this = $(e.target),
            self = this,
            $card = $this.parents('.module-card'),
            roster = $card.attr('data-col-name'),
            $cardWrapper = $card.find('.card-inner-wrapper'),
            $input = $this.find('.add-item-name.tt-input'),
            $addBtn = $this.find('.save-card-item'),
            $errorBox = $this.find('.error-text'),
            item = $input.val(),
            url = this.data.url + this.data.teamName + '/rosters/' + roster + '/users',
            template = Handlebars.compile(this.data.cardInnerTemplate),
            pillTemplate = Handlebars.compile(this.data.serviceItemTemplate);

        if (!item) {
          return false;
        }

        $addBtn.addClass('loading disabled').prop('disabled', true);
        $errorBox.empty();

        if (roster === 'admins') {
          url = this.data.url + this.data.teamName + '/admins';
        } else if (roster === 'services') {
          url = this.data.url + this.data.teamName + '/services';
        }

        $.ajax({
          type: 'POST',
          url: url,
          contentType: 'application/json',
          dataType: 'html',
          data: JSON.stringify({name: item})
        }).done(function(data){
          var data = JSON.parse(data);

          if (roster === 'services') {
            $cardWrapper.append(pillTemplate(item));
          } else {
            var blankModel = {
              newItem: true,
              admin: roster === 'admins' ? true : false,
              user: data
            }

            if (!data.contacts.call) {
              oncall.alerts.createAlert('Warning: ' + data.full_name + ' does not have a phone number in the database! Please ask them to update it through Cinco/LDAP.', 'danger', this.data.$page);
            }

            $cardWrapper.append(template(blankModel));
          }
          self.toggleAddItem.call($this);
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Add failed.';
          $errorBox.text(error);
        }).always(function(){
          $addBtn.removeClass('loading disabled').prop('disabled', false);
        });
      },
      removeCardItem: function($modal, $caller){
        var $card = $caller.parents('.module-card'),
            $cardInner = $caller.parents('.card-inner'),
            roster = $card.attr('data-col-name'),
            $modalBody = $modal.find('.modal-body'),
            $cta = $modal.find('.modal-cta'),
            name = $cardInner.attr('data-card-name'),
            url = this.data.url + this.data.teamName + '/rosters/' + roster + '/users/' + name,
            $pill;

        $cta.addClass('loading disabled').prop('disabled', true);

        if (roster === 'admins') {
          url = this.data.url + this.data.teamName + '/admins/' + name;
        } else if (roster === 'services') {
          $pill = $caller.parents('.pill');
          name = $pill.attr('data-service-name');
          url = this.data.url + this.data.teamName + '/services/' + name;
        }

        $.ajax({
          type: 'DELETE',
          url: url,
          dataType: 'html'
        }).done(function(e){
          $modal.modal('hide');
          if (roster === 'services') {
            $pill.remove();
          } else {
            $cardInner.remove();
          }
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
          oncall.alerts.createAlert(error, 'danger', $modalBody);
        }).always(function(){
          $cta.removeClass('loading disabled').prop('disabled', false);
        });
      },
      toggleRotation: function(e){
        var $this = $(e.currentTarget),
            self = this,
            $card = $this.parents('.module-card'),
            roster = $card.attr('data-col-name'),
            user = $this.parents('.card-inner').attr('data-card-name'),
            url = this.data.url + this.data.teamName + '/rosters/' + roster + '/users/' + user,
            method = $this.attr('data-in-rotation') === 'true' ? false : true;

        $this.addClass('loading disabled').prop('disabled', true);

        $.ajax({
          type: 'PUT',
          url: url,
          dataType: 'html',
          contentType: 'application/json',
          data: JSON.stringify({'in_rotation': method})
        }).done(function(){
          $this.attr('data-in-rotation', method);
        }).fail(function(data){
          var error = (typeof JSON.parse(data.responseText) === "object") ? JSON.parse(data.responseText).description : data.responseText || 'Update failed.';
          oncall.alerts.createAlert(error, 'danger');
        }).always(function(){
          $this.removeClass('loading disabled').prop('disabled', false);
        });
      }
    },
    schedules: {
      data: {
        $page: $('.content-wrapper'),
        calendar: '#calendar-container',
        $calendar: null,
        url: '/api/v0/teams/',
        schedulesUrl: '/api/v0/schedules/',
        pageSource: $('#team-schedules-template').html(),
        moduleScheduleTemplate: $('#module-schedule-template').html(),
        moduleScheduleCreateTemplate: $('#module-schedule-create-template').html(),
        moduleScheduleWrapper: '.module-schedule-wrapper',
        addScheduleContainer: '.add-schedule-container',
        scheduleItem: '.module-card',
        addScheduleItem: '#add-schedule',
        deleteScheduleItem: '.delete-schedule-item',
        editScheduleItem: '.edit-schedule-item',
        saveSchedule: '#save-schedule',
        scheduleCreateForm: '.module-schedule-create',
        rotationItemTemplate: $('#rotation-item-template').html(),
        rotationItem: '.rotation-item',
        removeRotationItem: '.remove-rotation-item',
        addRotationItem: '.add-rotation-item',
        scheduleAdvanced: '.schedule-advanced',
        previewSchedule: '.preview-schedule',
        scheduleCount: '.schedule-count',
        moduleSchedule: '.module-schedule',
        toggleAdvanced: '.toggle-advanced',
        toggleScheduleView: '.toggle-schedule-view',
        populateSchedulesModal: '#populate-schedule-modal',
        teamName: null,
        events: []
      },
      init: function(name){
        Handlebars.registerPartial('module-schedule', this.data.moduleScheduleTemplate);
        Handlebars.registerPartial('module-schedule-create', this.data.moduleScheduleCreateTemplate);
        Handlebars.registerPartial('rotation-item', this.data.rotationItemTemplate);
        this.data.teamName = decodeURIComponent(name);
        this.data.events = [];
        this.getData(name);
      },
      events: function(){
        router.updatePageLinks();
        this.data.$page.on('click', this.data.addScheduleItem, this.addScheduleItem.bind(this));
        this.data.$page.on('submit', this.data.scheduleCreateForm, this.saveSchedule.bind(this));
        this.data.$page.on('click', this.data.addRotationItem, this.addRotationItem.bind(this));
        this.data.$page.on('click', this.data.editScheduleItem, this.editScheduleItem.bind(this));
        this.data.$page.on('change', this.data.toggleAdvanced, this.toggleScheduleCreateMode.bind(this));
        this.data.$page.on('click', this.data.removeRotationItem, this.removeRotationItem.bind(this));
        this.data.$page.on('click', this.data.previewSchedule, this.previewSchedule.bind(this));
        this.data.$page.on('click', this.data.toggleScheduleView, this.toggleScheduleView);
      },
      getData: function(name){
        var self = this,
            events = this.data.events,
            rows = 1,
            msPerMinute = 60 * 1000,
            msPerHour = msPerMinute * 60,
            msPerDay = msPerHour * 24,
            msPerWeek = msPerDay * 7;

        $.getJSON(this.data.url + this.data.teamName).done(function(data){
          // shim api response for calendar / modules
          for (var i in data.rosters) {
            if (data.rosters.hasOwnProperty(i)) {
              var item = data.rosters[i];
              for (var k = 0; k < item.schedules.length; k++) {
                var schedule = item.schedules[k];
                schedule.is_12_hr = !schedule.advanced_mode && schedule.events.length > 1 ? true : false;
                for (var j = 0, eventItem; j < schedule.events.length; j++) {
                  eventItem = schedule.events[j];
                  eventItem.start = eventItem.start * 1000;
                  eventItem.duration = eventItem.duration * 1000;
                  eventItem.end = eventItem.start + eventItem.duration;
                  eventItem.role = schedule.role;
                  eventItem.parentId = schedule.id;
                  eventItem.roster = i;
                  eventItem.displayString = self.formatScheduleEventDisplay(eventItem);
                  events.push(eventItem);
                  if ( rows < Math.ceil(eventItem.start / msPerWeek) ) {
                    rows = Math.ceil(eventItem.start / msPerWeek);
                  }
                }
                schedule.events.sort(function(a, b){ return a.start > b.start ? 1 : -1 });
              }
            }
          }
          data.rows = rows;
          data.timezones = oncall.data.timezones;
          data.roles = oncall.data.roles;
          self.data.teamData = data;
          self.renderPage(data);
          self.renderPopulateScheduleModal.call(self);
          oncall.recentlyViewed.setItem(self.data.teamName);
        }).fail(function(error){
          var data = {
            error: true,
            error_code: error.status,
            error_status: error.statusText,
            error_text: name + ' team not found'
          }
          self.renderPage(data);
        });
      },
      renderPage: function(data){
        var template = Handlebars.compile(this.data.pageSource),
            self = this,
            events = this.data.events;

        this.data.$page.html(template(data));
        this.events();
        this.renderScheduleCount();
        self.data.$calendar = $(self.data.calendar);
        self.data.$calendar.incalendar({
          currentView: 'template',
          toolbar: false,
          drag: false,
          persistSettings: false,
          events: events,
          rowCount: data.rows,
          onEventMouseover: function($el, evt){
            $('.module-schedule[data-id=' + evt.parentId + ']').attr('data-highlighted', true);
            self.data.$calendar.find('[data-parent-id="' + evt.parentId + '"]').attr('data-highlighted', true);
          },
          onEventMouseout: function($el, evt){
            $('.module-schedule[data-id=' + evt.parentId + ']').attr('data-highlighted', false);
            self.data.$calendar.find('[data-parent-id="' + evt.parentId + '"]').attr('data-highlighted', false);
          }
        });
      },
      addScheduleItem: function(e, data){
        var template = Handlebars.compile(this.data.moduleScheduleCreateTemplate),
            $container = $(e.target).parents().find(this.data.addScheduleContainer),
            teamData = $.extend(true, {}, this.data.teamData);

        if (data) {
          for (var i = 0, item, weekObject; i < data.events.length; i++) {
            item = data.events[i];
            weekObject = Handlebars.helpers.timeSince(item.start, 'weekObject');
            item.startDayIndex = weekObject.daysSince;
            item.startTime = weekObject.hoursSince + ':' + weekObject.minutesSince;
            item.durationMs = item.end - item.start;
            item.duration = parseFloat((item.durationMs / 86400000).toFixed(2));
            item.durationUnit = 'days';
          }
          if (data.advanced_mode === 0 && data.events.length > 1) {
            data.is_12_hr = true;
            data.events[0].totalEvents = data.events.length; // Since the UI only uses the first event to create the schedule card, we assign the total length of events so the UI knows if the event is weekly or biweekly
          }
          teamData.selected_schedule = data;
        }

        $container.prepend(template(teamData));
      },
      editScheduleItem: function(e){
        var $scheduleItem = $(e.target).parents(this.data.scheduleItem),
            data = JSON.parse($scheduleItem.attr('data-model'));

        this.addScheduleItem(e, data);
      },
      toggleScheduleCreateMode: function(e){
        var $toggle = $(e.target),
            $form = $toggle.parents(this.data.scheduleItem);

        $form.attr('data-advanced', $toggle.prop('checked') ? '1' : '0');
      },
      addRotationItem: function(e){
        var template = Handlebars.compile(this.data.rotationItemTemplate),
            $container = $(e.target).parents(this.data.scheduleAdvanced),
            $lastItem = $container.find(this.data.rotationItem + ':last'),
            $btn = $container.find(this.data.addRotationItem),
            $clone;

        if ($lastItem.length) {
          $clone = $lastItem.clone();

          $clone.find('select').each(function(i, item){
            $(item).val($lastItem.find('select').eq(i).val());
          });
          $btn.before($clone);
        } else {
          $btn.before(template());
        }
      },
      removeRotationItem: function(e){
        $(e.target).parents(this.data.rotationItem).remove();
      },
      formatScheduleData: function($form){
        var self = this,
            advancedMode = parseInt($form.attr('data-advanced')),
            $rotationItems = $form.find('.schedule-' + (advancedMode ? 'advanced' : 'basic') + ' ' + this.data.rotationItem),
            $formActions = $form.find('.schedule-actions'),
            msPerMinute = 60 * 1000,
            msPerHour = msPerMinute * 60,
            msPerDay = msPerHour * 24,
            msPerWeek = msPerDay * 7,
            roster = $form.find('.schedule-roster').val(),
            id = parseInt($form.attr('data-edit-id')),
            role = $form.find('.schedule-role').val(),
            weekNum = 0,
            curCalRows = this.data.$calendar.incalendar('getCalRowCount'),
            curStartVal,
            events = [],
            msMapping = {
              'seconds': 1000,
              'minutes': msPerMinute,
              'hours': msPerHour,
              'days': msPerDay,
              'weeks': msPerWeek
            };

        if ($rotationItems.length === 0) {
          oncall.alerts.createAlert('Please add a schedule row.', 'danger', $formActions, 'before');
          return;
        }

        $rotationItems.each(function(i){
          var $this = $(this),
              $startDay = $this.find('.rotation-start-day option:selected'),
              startDay = $startDay.attr('data-index'),
              startTime = $this.find('.rotation-start-time').val(),
              $endVal = $this.find('.rotation-end-val'),
              $endDuration = $this.find('.rotation-end-duration option:selected'),
              is12Hr = $('#twelve-hour').prop('checked'),
              startVal = 0,
              endVal = 0;

          if (startDay) {
            startVal += startDay * msPerDay;
          }

          if ( isNaN(Date.parse(new Date('2017/01/01 ' + startTime))) ) {
            oncall.alerts.createAlert('Invalid start time.', 'danger', $formActions, 'before');
            return;
          }

          startVal += (parseInt(startTime.split(':')[0]) + (parseInt(startTime.split(':')[1]) / 60))  * msPerHour;

          if (advancedMode) {
            // Advanced schedule
            if (startVal <= curStartVal) {
              weekNum++;
            }
            curStartVal = startVal;
            startVal += weekNum * msPerWeek;
            endVal += $endVal.val() * msMapping[$endDuration.val()];
            var event = {
              roster: roster,
              index: i,
              parentId: id,
              role: role,
              start: startVal,
              end: startVal + endVal,
              duration: endVal
            }
            event.displayString = self.formatScheduleEventDisplay(event);
            events.push(event);
          } else {
            // Basic schedule
            if (is12Hr) {
              // Basic 12 hour schedule
              var ms12Hr = msPerDay / 2;
              for (var n = 0; n < parseInt($endDuration.val()); n++) {
                var event = {
                  roster: roster,
                  index: n,
                  parentId: id,
                  role: role,
                  start: startVal + (msPerDay * n),
                  end: startVal + ms12Hr + (msPerDay * n),
                  duration: ms12Hr
                }
                event.displayString = self.formatScheduleEventDisplay(event);
                events.push(event);
              }
              weekNum = Math.round(events[events.length-1].end / msPerWeek);
            } else {
              endVal += parseInt($endDuration.val()) * msPerDay;
              var event = {
                roster: roster,
                index: i,
                parentId: id,
                role: role,
                start: startVal,
                end: startVal + endVal,
                duration: endVal
              }
              event.displayString = self.formatScheduleEventDisplay(event);
              events.push(event);
            }
          }
        });

        if (curCalRows < weekNum + 1) {
          this.data.$calendar.incalendar('addCalendarRows', weekNum + 1 - curCalRows); // Add calendar rows to display formatted events
        }

        return events;
      },
      formatScheduleEventDisplay: function(evt){
        return evt.roster + ' ' + Handlebars.helpers.timeSince(evt.start, 'toString') + ' to ' + Handlebars.helpers.timeSince(evt.end, 'toString');
      },
      previewSchedule: function(e){
        var $form = $(e.target).parents(this.data.scheduleItem),
            events = this.formatScheduleData($form),
            existingEvents = $.extend(true, [], this.data.events),
            editId = parseInt($form.attr('data-edit-id'));

        if (events.length) {
          if (editId) {
            for (var i = existingEvents.length-1; i--;) {
              if (existingEvents[i].parentId === editId) {
                existingEvents.splice(i, 1);
              }
            }
          }
          previewEvents = existingEvents.concat(events);
          this.data.$calendar.incalendar('refreshCalendarEvents', previewEvents, true);
        }
      },
      saveSchedule: function(e){
        // Creates new schedule or updates existing schedule based on the 'data-edit-id' field of the add schedule form

        e.preventDefault();

        var self = this,
            $form = $(e.target),
            $cta = $form.find(this.data.saveSchedule),
            template = Handlebars.compile(this.data.moduleScheduleTemplate),
            roster = $form.find('.schedule-roster').val(),
            role = $form.find('.schedule-role').val(),
            threshold = $form.find('.auto-populate-threshold').val() || 21,
            timezone = $form.find('.schedule-timezone').val(),
            id = parseInt($form.attr('data-edit-id')),
            advancedMode = parseInt($form.attr('data-advanced')),
            events = this.formatScheduleData($form),
            url = id ? this.data.schedulesUrl + id : this.data.url + this.data.teamName + '/rosters/' + roster + '/schedules',
            method = id ? 'PUT' : 'POST',
            submitModel = {
              timezone: 'US/Pacific',
              roster: roster,
              role: role,
              auto_populate_threshold: threshold,
              advanced_mode: advancedMode,
              team: this.data.teamName,
              events: $.extend(true, [], events).map(function(i){
                // remove keys needed for calendar drawing but not API
                // convert ms to seconds for api
                i.start = i.start / 1000;
                i.end = i.end / 1000;
                i.duration = i.duration / 1000;
                delete i.user;
                delete i.index;
                delete i.role;
                return i;
              })
            }

        if (events.length) {
          $cta.addClass('loading disabled').prop('disabled', true);

          $.ajax({
            type: method,
            url: url,
            contentType: 'application/json',
            dataType: 'html',
            data: JSON.stringify(submitModel)
          }).done(function(data){
            // convert times back to MS for ui
            submitModel.events.map(function(item){
              item.start = item.start * 1000;
              item.end = item.end * 1000;
              item.duration = item.duration * 1000;
            });

            if (id) {
              // save was an update of existing schedule
              self.data.events = self.data.events.filter(function(i){
                // remove events with the parent ID matching schedule ID
                return i.parentId !== id;
              });

              self.data.events = self.data.events.concat(events);
              $('.module-schedule[data-id="'+ id +'"]').remove();
              submitModel.id = id;
              self.data.$page.find(self.data.moduleScheduleWrapper).append(template(submitModel));
              self.data.$calendar.incalendar('refreshCalendarEvents', self.data.events, true);
            } else {
              // new schedule
              data = JSON.parse(data);
              submitModel.id = data.id;
              for (var i = 0; i < events.length; i++) {
                events[i].parentId = data.id;
                events[i].displayString = self.formatScheduleEventDisplay(events[i]);
              }
              self.data.events = self.data.events.concat(events);
              self.data.$calendar.incalendar('refreshCalendarEvents', self.data.events, true);
              self.data.$page.find(self.data.moduleScheduleWrapper).append(template(submitModel));
              self.renderScheduleCount();
            }
            $form.remove();
          }).fail(function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Request failed.';
            oncall.alerts.createAlert(error, 'danger');
          }).always(function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
          });
        }
      },
      deleteScheduleItem: function($modal, $caller){
        var self = this,
            $cta = $modal.find('.modal-cta'),
            id = parseInt($caller.attr('data-schedule-id')),
            $scheduleItem = this.data.$page.find(this.data.scheduleItem + '[data-id="' + id + '"]'),
            $editSchedule = $caller.parents(this.data.scheduleItem),
            $modalBody = $modal.find('.modal-body'),
            roster = $scheduleItem.attr('data-roster'),
            role = $scheduleItem.attr('data-role'),
            url = this.data.schedulesUrl + id;

        if (id) {
          $cta.addClass('loading disabled').prop('disabled', true);

          $.ajax({
            type: 'DELETE',
            url: url,
            dataType: 'html'
          }).done(function(e){
            self.data.events = self.data.events.filter(function(i){
              // remove events with the parent ID matching schedule ID
              return i.parentId !== id;
            });
            $modal.modal('hide');
            $scheduleItem.remove();
            $editSchedule.remove();
            self.renderScheduleCount();
          }).fail(function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
            oncall.alerts.createAlert(error, 'danger', $modalBody);
          }).always(function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
            self.data.$calendar.incalendar('refreshCalendarEvents', self.data.events, true);
          });
        } else {
          $modal.modal('hide');
          $editSchedule.remove();
          self.data.$calendar.incalendar('refreshCalendarEvents', self.data.events, true);
        }
      },
      renderScheduleCount: function(){
        $(this.data.scheduleCount).text($(this.data.moduleScheduleWrapper).find(this.data.scheduleItem).length);
      },
      toggleScheduleView: function(){
        var $this = $(this).parents('[data-collapsed]');
        $this.attr('data-collapsed', $this.attr('data-collapsed') === "true" ? false : true);
      },
      renderPopulateScheduleModal: function(e){
        var self = this,
            $modal = $(self.data.populateSchedulesModal),
            $modalDate = $modal.find('#populate-schedule-date'),
            $modalThreshold = $modal.find('#populate-schedule-threshold'),
            $modalBtn = $modal.find('#populate-schedule-btn'),
            $modalTitle = $modal.find('.modal-title'),
            $calContainer = $modal.find('#modal-calendar-container'),
            scheduleData,
            scheduleId,
            threshold,
            now = moment();

        $modal.on('shown.bs.modal', function(e){
          scheduleData = JSON.parse($(e.relatedTarget).parents(self.data.scheduleItem).attr('data-model'));
          scheduleId = scheduleData.id;
          threshold = scheduleData.auto_populate_threshold;

          $calContainer.incalendar({
            eventsUrl: '/api/v0/events',
            getEventsUrl: '/api/v0/events?team__eq=' + self.data.teamName,
            readOnly: true,
            persistSettings: false,
            onEventGet: function(events, $cal){
              $cal.find('[data-schedule-id="' + scheduleId + '"]').attr('data-highlighted', true);
            }
          });

          $calContainer.find('[data-schedule-id="' + scheduleId + '"]').attr('data-highlighted', true);
          $modal.attr('data-schedule-id', scheduleId);
          $modalThreshold.text(threshold + ' Days');
          $modalDate.val(now.format('YYYY/MM/DD'));
        }).on('hidden.bs.modal', function(e){
          $(this).find('.alert').remove();
        });

        $modalBtn.on('click', function(){
          var date = new Date($modalDate.val());

          if ( isNaN(Date.parse(date)) ) {
            oncall.alerts.createAlert('Invalid date.', 'danger', $modal.find('.modal-body'));
          } else {
            self.populateSchedules(date.valueOf(), $(this), $modal);
          }
        });
      },
      populateSchedules: function(date, $cta, $modal){
        var date = (date || Date.now()) / 1000,
            self = this,
            $calContainer = $modal.find('#modal-calendar-container'),
            scheduleId = $modal.attr('data-schedule-id'),
            url = this.data.schedulesUrl + scheduleId + '/populate';

        $cta.addClass('loading disabled').prop('disabled', true);
        $.ajax({
          type: 'POST',
          url: url,
          contentType: 'application/json',
          dataType: 'html',
          data: JSON.stringify({start:date})
        }).done(function(data){
          oncall.alerts.removeAlerts();
          oncall.alerts.createAlert('Schedule successfully populated.', 'success', $modal.find('.modal-body'));
          $calContainer.data('incalendar', null).incalendar({
            eventsUrl: '/api/v0/events',
            getEventsUrl: '/api/v0/events?team__eq=' + self.data.teamName,
            readOnly: true,
            onEventGet: function(events, $cal){
              $cal.find('[data-schedule-id="' + scheduleId + '"]').attr('data-highlighted', true);
            }
          });
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Populate failed.';
          oncall.alerts.createAlert(error, 'danger', $modal.find('.modal-body'));
        }).always(function(){
          $cta.removeClass('loading disabled').prop('disabled', false);
        });
      }
    }
  },
  settings: {
    data: {
      $page: $('.content-wrapper'),
      url: '/api/v0/users/',
      pageSource: $('#settings-template').html(),
      $form: '#user-settings-form',
      settingsSubheaderTemplate: $('#settings-subheader-template').html(),
      subheaderWrapper: '.subheader-wrapper'
    },
    init: function(){
      Handlebars.registerPartial('settings-subheader', this.data.settingsSubheaderTemplate);
      this.getData();
    },
    events: function(){
      router.updatePageLinks();
      this.data.$page.on('submit', this.data.$form, this.updateSettings.bind(this));
    },
    getData: function(e){
      if (oncall.data.user) {
        $.get(this.data.url + oncall.data.user, this.renderPage.bind(this));
      } else {
        router.navigate('/');
      }
    },
    renderPage: function(data){
      var template = Handlebars.compile(this.data.pageSource);

      data.timezones = oncall.data.timezones;
      this.data.$page.html(template(data));
      this.events();
    },
    updateSettings: function(e){
      e.preventDefault();
      var $form = $(e.target),
          $cta = $form.find('button[type="submit"]'),
          url = this.data.url + oncall.data.user,
          data = $form.find('select[name="time_zone"]').val();

      $cta.addClass('loading disabled').prop('disabled', true);

      $.ajax({
        type: 'PUT',
        url: url,
        dataType: 'html',
        contentType: 'application/json',
        data: JSON.stringify({time_zone: data})
      }).done(function(){
        oncall.data.userTimezone = data;
        oncall.alerts.createAlert('Settings saved.', 'success', $form);
      }).fail(function(data){
        var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Update failed.';
        oncall.alerts.createAlert(error, 'danger');
      }).always(function(){
        $cta.removeClass('loading disabled').prop('disabled', false);
      });
    },
    notifications: {
      data: {
        $page: $('.content-wrapper'),
        url: '/api/v0/users/',
        typesUrl: '/api/v0/notification_types',
        notificationUrl: '/api/v0/notifications/',
        pageSource: $('#notifications-template').html(),
        moduleNotificationTemplate: $('#module-notification-template').html(),
        moduleNotificationCreateTemplate: $('#module-notification-create-template').html(),
        settingsSubheaderTemplate: $('#settings-subheader-template').html(),
        moduleNotificationsContainer: '.module-notifications-container',
        moduleNotificationsWrapper: '.module-notifications-wrapper',
        moduleNotification: '.module-notification',
        form: '.module-notification-create',
        addReminder: '#add-reminder',
        addNotification: '#add-notification',
        editNotification: '.edit-notification',
        saveNotification: '.save-notification',
        editReminder: '.edit-reminder',
        notificationCount: '.notification-count',
        notificationCreateContainer: '.notification-create-container',
        reminderCreateContainer: '.reminder-create-container',
        subheaderWrapper: '.subheader-wrapper',
        typeMap: {
          'oncall_reminder': 'starts',
          'offcall_reminder': 'ends',
          'event_created': 'created',
          'event_edited': 'edited',
          'event_deleted': 'deleted',
          'event_swapped': 'swapped',
          'event_substituted': 'substituted'
        }
      },
      init: function(){
        Handlebars.registerPartial('settings-subheader', this.data.settingsSubheaderTemplate);
        Handlebars.registerPartial('module-notification', this.data.moduleNotificationTemplate);
        Handlebars.registerPartial('module-notification-create', this.data.moduleNotificationCreateTemplate);
        this.getData();
      },
      events: function(){
        this.data.$page.on('submit', this.data.form, this.saveNotification.bind(this));
        this.data.$page.on('click', this.data.addNotification, this.addNotification.bind(this));
        this.data.$page.on('click', this.data.addReminder, this.addReminder.bind(this));
        this.data.$page.on('click', this.data.editNotification, this.editNotification.bind(this));
        this.data.$page.on('click', this.data.editReminder, this.editReminder.bind(this));
      },
      getData: function(){
        var self = this;

        if (oncall.data.user) {
          $.when(
            // Get data needed to render notifications.
            $.get(this.data.url + oncall.data.user + '/notifications'),
            $.get(this.data.url + oncall.data.user + '/teams'),
            $.get(this.data.typesUrl)
          ).done(function(notificationData, teamsData, types){
            types[0].map(function(i){
              if (typeof(self.data.typeMap[i.name]) !== 'undefined') {
                i.display = self.data.typeMap[i.name];
              }
              return i;
            });
            notificationData.notifications = notificationData[0];
            notificationData.types = types[0];
            notificationData.typeMap = self.data.typeMap;
            notificationData.roles = oncall.data.roles;
            notificationData.modes = oncall.data.modes;
            notificationData.teams = teamsData[0];
            self.data.notificationData = notificationData;
            self.renderPage.call(self, notificationData);
          });
        } else {
          router.navigate('/');
        }
      },
      renderPage: function(data){
        var template = Handlebars.compile(this.data.pageSource);

        this.data.$page.html(template(data));
        this.events();
        this.renderNotificationCounts();
      },
      renderNotificationCounts: function(){
        // Renders the count for notifications & reminders

        var self = this;

        $(this.data.notificationCount).text(function(){
          return $(this).parents(self.data.moduleNotificationsContainer).find(self.data.moduleNotificationsWrapper).find(self.data.moduleNotification).length;
        });
      },
      addNotification: function(e, data){
        var template = Handlebars.compile(this.data.moduleNotificationCreateTemplate),
            $container = $(e.target).parents().find(this.data.notificationCreateContainer),
            notificationData = this.data.notificationData;

        notificationData.selected = data;
        notificationData.createType = 'notification';
        $container.prepend(template(notificationData));
      },
      addReminder: function(e, data){
        var template = Handlebars.compile(this.data.moduleNotificationCreateTemplate),
            $container = $(e.target).parents().find(this.data.reminderCreateContainer),
            notificationData = this.data.notificationData;

        notificationData.selected = data;
        notificationData.createType = 'reminder';
        $container.prepend(template(notificationData));
      },
      formatNotificationData: function($form){
        var self = this,
            type = $form.data('type'),
            msPerMinute = 60 * 1000,
            msPerHour = msPerMinute * 60,
            msPerDay = msPerHour * 24,
            msPerWeek = msPerDay * 7,
            msMapping = {
              'seconds': 1000,
              'minutes': msPerMinute,
              'hours': msPerHour,
              'days': msPerDay,
              'weeks': msPerWeek
            },
            data = {};

        data.mode = $form.find('.notification-create-mode').val();

        // Set the value required to differentiate between notification and reminder based on type.

        if (type === 'reminder') {
          data.time_before = $form.find('.notification-create-time').val() * msMapping[$form.find('.notification-create-unit').val()] / 1000;
        } else {
          data.only_if_involved = true;
        }
        data.roles = [];
        $form.find('.notification-create-role').find('input[type="checkbox"]:checked').each(function(){
          data.roles.push($(this).val());
        });
        data.mode = $form.find('.notification-create-mode').val();
        data.type = $form.find('.notification-create-type').val();
        data.team = $form.find('.notification-create-team').val();

        for (var i = 0, item, keys = Object.keys(data); i < keys.length; i++) {
          item = data[keys[i]];
          if (!item || Array.isArray(item) && item.length === 0 || data.time_before !== 'undefined' && data.time_before <= 0) {
            oncall.alerts.createAlert('Invalid or missing field.');
            return;
          }
        }
        return data;
      },
      saveNotification: function(e){
        // Creates new notification or updates existing schedule based on the 'data-edit-id' field of the add notification form

        e.preventDefault();

        var self = this,
            $form = $(e.target),
            notification = this.formatNotificationData($form),
            type = notification.viewType = $form.data('type'),
            $cta = $form.find(this.data.saveNotification),
            template = Handlebars.compile(this.data.moduleNotificationTemplate),
            id = parseInt($form.attr('data-edit-id')),
            url = id ? this.data.notificationUrl + id : this.data.url + oncall.data.user + '/notifications';
            method = id ? 'PUT' : 'POST';

        if (notification) {
          oncall.alerts.removeAlerts();
          $.ajax({
            type: method,
            url: url,
            contentType: 'application/json',
            dataType: 'html',
            data: JSON.stringify(notification)
          }).done(function(data){
            if (id) {
              notification.id = id;
              $('.module-notification[data-id="'+ id +'"]').remove();
            } else {
              notification.id = JSON.parse(data).id;
            }
            notification.typeMap = self.data.typeMap;
            self.data.$page.find(self.data.moduleNotificationsWrapper + '[data-type=' + type + ']').append(template(notification));
            $form.remove();
            self.renderNotificationCounts();
          }).fail(function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Request failed.';
            oncall.alerts.createAlert(error, 'danger');
          }).always(function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
          });
        }
      },
      editNotification: function(e){
        var $moduleNotification = $(e.target).parents(this.data.moduleNotification),
            data = JSON.parse($moduleNotification.attr('data-model'));

        this.addNotification(e, data);
        oncall.multiSelect.updateSelectVal();
      },
      editReminder: function(e){
        var $moduleNotification = $(e.target).parents(this.data.moduleNotification),
            data = JSON.parse($moduleNotification.attr('data-model'));

        this.addReminder(e, data);
        oncall.multiSelect.updateSelectVal();
      },
      deleteNotification: function($modal, $caller){
        var self = this,
            $cta = $modal.find('.modal-cta'),
            id = parseInt($caller.attr('data-notification-id')),
            $moduleNotification = this.data.$page.find(this.data.moduleNotification + '[data-id="' + id + '"]'),
            $form = $caller.parents(this.data.form),
            $modalBody = $modal.find('.modal-body'),
            url = this.data.notificationUrl + id;

        if (id) {
          $cta.addClass('loading disabled').prop('disabled', true);

          $.ajax({
            type: 'DELETE',
            url: url,
            dataType: 'html'
          }).done(function(e){
            $modal.modal('hide');
            $form.remove();
            $moduleNotification.remove();
            self.renderNotificationCounts();
          }).fail(function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
            oncall.alerts.createAlert(error, 'danger', $modalBody);
          }).always(function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
          });
        } else {
          $modal.modal('hide');
          $form.remove();
        }
      }
    }
  },
  modal: {
    data: {
      $inputModal: $('#input-modal'),
      $teamEditModal: $('#team-edit-modal'),
      $confirmActionModal: $('#confirm-action-modal')
    },
    init: function(){
      this.setupCreateModal();
      this.setupConfirmModal();
      this.setupTeamEditModal();
    },
    setupConfirmModal: function(){
      var $modal = this.data.$confirmActionModal,
          $modalForm = $modal.find('.modal-form'),
          $modalInput = $modalForm.find('.create-input'),
          self = this,
          $btn,
          action;

      $modal.on('show.bs.modal', function(e){
        $btn = $(e.relatedTarget);
        action = $btn.attr('data-modal-action');
        $(this).find('.modal-title').text($btn.attr('data-modal-title'));
        $(this).find('.modal-body').text($btn.attr('data-modal-content'));
      });

      $modalForm.on('submit', function(e){
        e.preventDefault();

        self.callModalActions(action, $modal, $btn);
      });
    },
    setupCreateModal: function(){
      var $modal = this.data.$inputModal,
          $modalForm = $modal.find('.modal-form'),
          $modalInput = $modalForm.find('.create-input'),
          self = this,
          $btn,
          action;

      $modal.on('show.bs.modal', function(e){
        $btn = $(e.relatedTarget);
        action = $btn.attr('data-modal-action');
        $(this).find('.modal-title').text($btn.attr('data-modal-title'));
        if ($btn.attr('data-modal-placeholder')) {
          $modalInput.attr('placeholder', $btn.attr('data-modal-placeholder'));
        }
        $modalInput.val($btn.attr('data-modal-val'));
      }).on('shown.bs.modal', function(e){
        $modalInput.trigger('focus');
      });

      $modalForm.on('submit', function(e){
        e.preventDefault();
        var val = $(this).find('.create-input').val();
        $modal.find('.alert').remove();
        self.callModalActions(action, $modal, $btn, val);
      });

      $modal.on('hide.bs.modal', function(){
        $modal.find('.alert').remove();
        $modalForm[0].reset();
      });
    },
    setupTeamEditModal: function(){
      var $modal = this.data.$teamEditModal,
          $modalForm = $modal.find('.modal-form'),
          $teamName = $modalForm.find('#team-name'),
          $teamEmail = $modalForm.find('#team-email'),
          $teamSlack = $modalForm.find('#team-slack'),
          $teamTimezone = $modalForm.find('#team-timezone'),
          self = this,
          $btn,
          action;

      $modal.on('show.bs.modal', function(e){
        $btn = $(e.relatedTarget);
        action = $btn.attr('data-modal-action');
        $(this).find('.modal-title').text($btn.attr('data-modal-title'));
        $teamName.val($btn.attr('data-modal-name'));
        $teamEmail.val($btn.attr('data-modal-email'));
        $teamSlack.val($btn.attr('data-modal-slack'));
        if ($btn.attr('data-modal-timezone')) {
          $teamTimezone.val($btn.attr('data-modal-timezone'));
        }
      }).on('shown.bs.modal', function(e){
        $modalForm.find('#team-name').trigger('focus');
      });

      $modalForm.on('submit', function(e){
        e.preventDefault();
        $modal.find('.alert').remove();
        self.callModalActions(action, $modal, $btn, $modalForm);
      });

      $modal.on('hide.bs.modal', function(){
        $modal.find('.alert').remove();
        $modalForm[0].reset();
      });
    },
    callModalActions: function(action, $modal, $caller, args){
      // calls the function specified by modal initiator
      var actionArray = action.split('.'),
          actionFn = actionArray.pop(),
          ctx = window;

      for(var i = 0; i < actionArray.length; i++) {
        ctx = ctx[actionArray[i]];
      }
      ctx[actionFn].call(ctx, $modal, $caller, args);
    }
  },
  registerHandlebarHelpers: function(){
    Handlebars.registerHelper('isSelected', function(val, check){
      return val === check ? 'selected': '';
    });

    Handlebars.registerHelper('isChecked', function(val, check){
      return val === check ? 'checked': '';
    });

    Handlebars.registerHelper('isCheckedMulti', function(val, checkArray){
      return val && checkArray && checkArray.indexOf(val) !== -1 ? 'checked' : '';
    });

    Handlebars.registerHelper('isEqual', function(val1, val2, opts){
      return val1 === val2 ? opts.fn(this) : opts.inverse(this);
    });

    Handlebars.registerHelper('ifNotEmpty', function(val, opts){
      return val && Object.keys(val).length !== 0 ? opts.fn(this) : opts.inverse(this);
    });

    Handlebars.registerHelper('ifExists', function(val, opts){
      return typeof(val) !== 'undefined' ? opts.fn(this) : opts.inverse(this);
    });

    Handlebars.registerHelper('convertUnixTime', function(val, format){
      // Format = moment.js date format ( SEE: https://momentjs.com/docs/#/displaying/format/ )
      if (oncall.data.userTimezone) {
        return format && typeof(format) === 'string' ? moment.tz(val * 1000, oncall.data.userTimezone).format(format) : moment.tz(val * 1000, oncall.data.userTimezone).toString();
      } else {
        return format && typeof(format) === 'string' ? moment(val * 1000).format(format) : moment(val * 1000).toString();
      }
    });

    Handlebars.registerHelper('getObjectLength', function(obj){
      // returns number of keys in object
      return Object.keys(obj).length;
    });

    Handlebars.registerHelper('inArray', function(val, arr, opts){
      // checks if given value is contained within the given array
      return arr.indexOf(val) !== -1 ? opts.fn(this) : opts.inverse(this);
    });

    Handlebars.registerHelper('stringify', function(obj){
      // converts object to JSON string
      return JSON.stringify(obj);
    });

    Handlebars.registerHelper('stripHash', function(str){
      // removes hash tag from string
      return str.replace('#', '');
    });

    Handlebars.registerHelper('getUserInfo', function(user, users, key){
      // accepts a user name, the user object containing all user contact info, and the key you need the value for
      if (!user || !users || !key || !users[user.name]) {
        return "Unknown";
      }
      if (key.indexOf('.') !== -1) {
        var keyArray = key.split('.'),
            endKey = keyArray.pop(),
            ctx = users[user.name];

        for(var i = 0; i < keyArray.length; i++) {
          ctx = ctx[keyArray[i]];
        }
        return ctx[endKey] || "Unknown";
      } else {
        return users[user.name][key] || "Unknown";
      }
    });

    Handlebars.registerHelper('timeSince', function(val, type){
      // accepts millisecond value and returns time since sunday 00:00 in object form or string form
      var daysShort = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'],
          val = val / 1000, //#TODO: change logic from seconds to ms
          daysSince = Math.floor(val / 86400) % 7,
          hoursSince = Math.floor((val % 86400) / 3600),
          minutesSince = Math.floor(((val % 86400) % 3600) / 60);

      if (type === 'weekObject') {
        return {
          daysSince: daysSince,
          hoursSince: hoursSince < 10 ? '0' + hoursSince : hoursSince,
          minutesSince: minutesSince < 10 ? '0' + minutesSince : minutesSince
        }
      } else {
        return daysShort[daysSince] + ' ' + hoursSince + ':' + (minutesSince < 10 ? '0' + minutesSince : minutesSince);
      }
    });

    Handlebars.registerHelper('scaleSeconds', function(val, format){
      // accepts seconds value and scales it to the highest possible display.
      // returns unit or duration.

      var sPerMinute = 60,
          sPerHour = sPerMinute * 60,
          sPerDay = sPerHour * 24,
          sPerWeek = sPerDay * 7,
          result;

      if (val % sPerWeek === 0) {
        result = {duration: val / sPerWeek, unit: 'weeks'};
      } else if (val % sPerDay === 0) {
        result = {duration: val / sPerDay, unit: 'days'};
      } else if (val % sPerHour === 0) {
        result = {duration: val / sPerHour, unit: 'hours'};
      } else if (val % sPerMinute === 0) {
        result = {duration: val / sPerMinute, unit: 'minutes'};
      } else {
        result = {duration: val, unit: 'seconds'};
      }

      return result[format];

    });
  },
  alerts: {
    data: {
      alertId: 'oncall-alert'
    },
    createAlert: function(alertText, type, $el, action, fixed){
      // params:
      //-- alertText: content of alert *REQUIRED* --string--
      //-- type: type of alert (coincides to color) --string--
        //---- 'danger' - red *default*
        //---- 'warning' - yellow
        //---- 'info' - blue
        //---- 'success' - green
      //-- $el: DOM element which the alert will be added to. Defaults to body --jQuery element--
      //-- action: jQuery action on the $el.
        //---- 'prepend' - inserts alert as first element inside $el *default*
        //---- 'append' - inserts alert at the end of the $el
        //---- 'before' - inserts alert as a sibling node before $el
        //---- 'after' - inserts alert as a sibling node after $el
      //-- fixed: alternate alert which is absolutely positioned at top center of the screen
      var alert,
          type = type || 'danger',
          $el = $el || $('.main'),
          action = action || 'prepend',
          fixed = fixed || '';

      if (!$('#' + this.data.alertId).length) {
        alert = '<div id="' + this.data.alertId + '" class="alert alert-'+ type +' alert-dismissible ' + fixed + '" role="alert"><button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button><span class="alert-content"></span></div>';
        $el[action](alert);
      }

      $('#' + this.data.alertId).find('.alert-content').html(alertText);
    },
    removeAlerts: function(){
      $('#' + this.data.alertId).remove();
    }
  },
  typeahead: {
    data: {
      url: '/api/v0/',
      field: 'input.typeahead'
    },
    init: function(urlType, changeCallback, team){
      var $field = $(this.data.field),
          self = this;

      $field.typeahead('destroy').each(function(){
        var $this = $(this),
            type = $this.attr('data-type') || 'users',
            results;

        if (type === 'services') {
          results = new Bloodhound({
            datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            remote: {
              url: self.data.url + type + '?name__startswith=%QUERY',
              wildcard: '%QUERY'
            }
          });
          $this.typeahead(null, {
            hint: true,
            async: true,
            highlight: true,
            source: results
          }).on('typeahead:select', function(){
            $(this).attr('value', $(this).val());
          });
        } else {
          var url = self.data.url + 'search?fields=' + type + '&keyword=%QUERY';
          if (team) {
            url += '&team=' + team;
          }
          results = new Bloodhound({
            datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            remote: {
              url: url,
              wildcard: '%QUERY',
              transform: function(response) {
                return response.users
              }
            }
          });
          $this.typeahead(null,
            {
              hint: true,
              async: true,
              highlight: true,
              display: 'name',
              source: results,
              templates: {
                suggestion: Handlebars.compile('<div> {{full_name}} <strong>[{{name}}]</strong> </div>')
              }
            });
        }
        if (changeCallback) {
          $this.on('typeahead:change', changeCallback);
        }
      });
    },
    destroy: function() {
      $(this.data.field).typeahead('destroy');
    }
  },
  isJson: function(str){
    try {
      JSON.parse(str);
    } catch (error) {
      return false;
    }
    return true;
  },
  multiSelect: {
    data: {
      $page: $('.content-wrapper'),
      selectContainer: '.multi-select',
      overlay: '.multi-select-overlay',
      options: '.multi-select-options',
      initial: '.multi-select-initial',
      initialVal: null
    },
    init: function(){
      this.data.$page.on('click', this.data.overlay, this.toggleOptions.bind(this));
      this.data.$page.on('change', this.data.options + ' input[type="checkbox"]', this.updateSelectVal.bind(this));
    },
    toggleOptions: function(e){
      var self = this,
          $el = $(e.target),
          $overlay = $el.siblings(this.data.options);

      e.stopPropagation();

      if ($overlay.hasClass('visible')) {
        $overlay.removeClass('visible');
        $(document).off('click.hideToggle');
      } else {
        $overlay.addClass('visible');
        $(document).on('click.hideToggle', function(e){
          if ($(e.target).parents(self.data.options).length === 0) {
            $el.siblings(self.data.options).removeClass('visible');
          }
        });
      }
    },
    updateSelectVal: function(e){
      var self = this,
          $multi = e ? $(e.target).parents(this.data.selectContainer) : $(this.data.selectContainer);

      $multi.each(function(){
        var $this = $(this),
            $initial = $this.find(self.data.initial),
            $options = $this.find(self.data.options),
            initialVal = self.data.initialVal = self.data.initialVal || $initial.val();

        $this.find('option').text(function(){
          var checkedOpts = $options.find('input[type="checkbox"]:checked');
          if (checkedOpts.length === 1) {
            return checkedOpts.val();
          } else if (checkedOpts.length > 1) {
            return checkedOpts.val() + ' (+' + (checkedOpts.length - 1) + ')';
          } else {
            return initialVal;
          }
        });
      });
    }
  }
}

oncall.init();
