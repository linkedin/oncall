var router = new Navigo(root = null, useHash = false);

var oncall = {
  data: {
    $body: $('body'),
    $page: $('.content-wrapper'),
    $createBtn: $('#create-btn'),
    $userInfoContainer: $('.user-info-container'),
    $loginForm: $('#navbar-form'),
    $logoutBtn: $('.logout'),
    $editAdvanced: $('.advanced-toggle'),
    $editModal: $('#team-edit-modal'),
    errorTemplate: $('#error-page-template').html(),
    loginUrl: '/login',
    logoutUrl: '/logout',
    user: $('body').attr('data-user'),
    userUrl: '/api/v0/users/',
    irisSettingsUrl: '/api/v0/iris_settings',
    rolesUrl: '/api/v0/roles/',
    timezonesUrl: '/api/v0/timezones/',
    modesUrl: '/api/v0/modes',
    roles: null,  // will be fetched from API
    irisSettings: null,  // will be fetched from API
    timezones: null,  // will be fetched from API
    modes: null,  // will be fetched from API
    userTimezone: null,
    userInfo: null,
    csrfKey: 'csrf-key',
    userInfoPromise: $.Deferred(),
    irisSettingsPromise: $.Deferred(),
    rolesPromise: $.Deferred(),
    timezonesPromise: $.Deferred(),
    modesPromise: $.Deferred()
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

    this.defineRoutes();
    this.events.call(this);
    this.registerHandlebarHelpers();
    this.getIrisSettings();
    this.data.irisSettingsPromise.done(function() {
      self.modal.init(self);
    });
    if (this.data.user && this.data.user !== 'None') {
      this.getUserInfo().done(this.getUpcomingShifts.bind(this));
    } else {
      this.data.userInfoPromise.resolve();
    }
    this.getRoles();
    this.getTimezones();
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
      dataType: 'html'
    }).done(function(data){
      var data = JSON.parse(data),
          token = data.csrf_token;

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
    }).fail(function(){
      oncall.alerts.createAlert('Invalid username or password.', 'danger');
    });
  },
  logout: function(){
    var url = this.data.logoutUrl,
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
      location.reload();
    }).fail(function(){
      oncall.alerts.createAlert('Logout failed.', 'danger');
    });
  },
  toggleAdvanced: function() {
    var advanced = this.data.$editModal.attr('data-advanced');
    this.data.$editModal.attr('data-advanced', advanced === 'false' ? 'true' : 'false');
  },
  getUserInfo: function(){
    var self = this;
    return $.get(this.data.userUrl + this.data.user).done(function(data){
      self.data.userInfo = data;
      self.data.user = data.name;
      self.data.userIsGod = data.god;
      self.data.userTimezone = data.time_zone;
      self.data.userInfoPromise.resolve();
      self.renderUserInfo.call(self, data);
    });
  },
  getIrisSettings: function (){
    var self = this;
    return $.get(this.data.irisSettingsUrl).done(function(data){
      self.data.irisSettings = data;
      self.data.irisSettingsPromise.resolve();
    });
  },
  renderUserInfo: function(data){
    var $body = this.data.$body,
        $nav = $body.find('#navbar'),
        $container = $nav.find('.user-info-container');

    $body.attr('data-user', data.name);
    $nav.find('.user-dashboard-link').attr('href', '/dashboard/' + data.name);
    //if data.photo_url is null replace with default headshot
    data.photo_url = data.photo_url || '/static/images/headshot-blank.jpg';
    $container
      .find('.profile-picture').removeClass('placeholder').attr('src', data.photo_url)
      .end()
      .find('.user-settings-link').attr('href', '/user/' + data.name);
  },
  getRoles: function(){
    var self = this;
    $.get(this.data.rolesUrl).done(function(data){
      self.data.roles = data.sort(function(a, b) {
        return a.display_order - b.display_order;
      });
      self.data.rolesPromise.resolve();
    });
  },
  getModes: function() {
      var self = this;
      $.get(this.data.modesUrl).done(function (data) {
          self.data.modes = data;
          self.data.modesPromise.resolve();
      });
  },
  getTimezones: function() {
    var self = this;
    $.get(this.data.timezonesUrl).done(function (data) {
      self.data.timezones = data;
      self.data.timezonesPromise.resolve();
    });
  },
  getUpcomingShifts: function(){
    var self = this,
        limit = 3; // Limit number of results

    $.get(this.data.userUrl + this.data.user + '/upcoming', { limit: limit }).done(function(data){
      self.renderUpcomingShifts.call(self, data);
    });
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
    this.data.$editAdvanced.on('click', this.toggleAdvanced.bind(this));
  },
  updateTitleTag: function(newTitle){
    if(newTitle == ""){
      document.title = "Oncall";
    }
    else{
      document.title = unescape(newTitle) + " - Oncall";
    }

  },
  defineRoutes: function(){
    var self = this;
    router.on({
      '/teams/all': function(){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.browse.init();
        self.updateTitleTag("All teams");
      },
      '/team/:name/info': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.team.init(params.name, 'info');
        self.team.info.init(params.name);
        self.updateTitleTag(params.name + "  team info");
      },
      '/team/:name/schedules': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.team.init(params.name, 'schedules');
        self.team.schedules.init(params.name);
        self.updateTitleTag(params.name + " schedules");
      },
      '/team/:name/subscriptions': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.team.init(params.name, 'subscriptions');
        self.team.subscriptions.init(params.name);
        self.updateTitleTag(params.name + " subscriptions");
      },
      '/team/:name/audit': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.team.init(params.name, 'audit');
        self.team.audit.init(params.name);
        self.updateTitleTag(params.name + " audit");
      },
      '/team/:name': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.team.init(params.name, 'calendar');
        self.team.calendar.init(params.name);
        self.updateTitleTag(params.name + " calendar");
      },
      '/dashboard/:name': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.dashboard.init(params.name);
        self.updateTitleTag(params.name + " dashboard");
      },
      '/user/:user/': function(){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.settings.init();
        self.updateTitleTag("");
      },
      '/user/:user/notifications': function(){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.settings.notifications.init();
        self.updateTitleTag("Notifications");
      },
      '/user/:user/ical_key': function(){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.settings.ical_key.init();
        self.updateTitleTag("Public Calendar Keys");
      },
      '/query/:query/:fields': function(params){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        self.data.$page.off(); //reset events on page init
        self.search.init(params);
        self.updateTitleTag("");
      },
      '*': function(){
        oncall.callbacks.onLogin = $.noop;
        oncall.callbacks.onLogout = $.noop;
        window.history.replaceState({},'home', '/');
        self.search.init();
        self.updateTitleTag("");
      }
    }).notFound(function(){
      router.navigate('/');
      self.updateTitleTag("");
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
    init: function(){
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
          self = this;

      $.get(teamsUrl, function(data){
        var pageModel = {
          data: data,
          name: name
        };
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
              };
              self.renderCardInner.call(self, model);
            });
          })(i);
        }
      }).fail(function(error){
        var data = {
          error: true,
          error_code: error.status,
          error_status: error.statusText,
          error_text: name + ' user not found'
        };
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
      //if data.photo_url is null replace with default headshot
      data.photo_url = data.photo_url || '/static/images/headshot-blank.jpg';
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
      cardInnerTemplate: $('#landing-teams-inner-template').html(),
      endpointTypes: ['services', 'teams', 'users'],
      searchForm: '.main-search',
      recentlyViewed: null,
      pinnedTeams: null
    },
    init: function(query){
      var $form,
          $input,
          typeaheadLimit = 10,
          services,
          teams,
          users,
          servicesCt,
          teamsCt,
          self = this,
          pinnedPromise = $.Deferred();

      Handlebars.registerPartial('dashboard-card-inner', this.data.cardInnerTemplate);
      oncall.callbacks.onLogin = function(){
        self.init();
      };
      this.data.recentlyViewed = oncall.recentlyViewed.getItems();
      if (oncall.data.user) {
        $.get('/api/v0/users/' + oncall.data.user + '/pinned_teams').done(function(response){
          self.data.pinnedTeams = response;
          pinnedPromise.resolve();
        });
      } else {
        pinnedPromise.resolve();
      }

      pinnedPromise.done(function() {
        self.renderPage();
        self.getTeamSummaries();
        $form = self.data.$page.find(self.data.searchForm);
        $input = $form.find('.search-input');

        if (query) {
          self.getData.call(self, query);
          $form.find('.search-input').val(decodeURIComponent(query.query));
        }

        services = new Bloodhound({
          datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
          queryTokenizer: Bloodhound.tokenizers.whitespace,
          remote: {
            url: self.data.url + '?keyword=%QUERY',
            rateLimitWait: 200,
            wildcard: '%QUERY',
            transform: function(resp){
              var newResp = [],
                keys = Object.keys(resp.services);

              servicesCt = keys.length;
              for (var i = 0; i < keys.length; i++) {
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
            url: self.data.url + '?keyword=%QUERY',
            rateLimitWait: 200,
            wildcard: '%QUERY',
            transform: function(resp){
              teamsCt = resp.teams.length;
              return resp.teams;
            }
          }
        });

        users = new Bloodhound({
          datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
          queryTokenizer: Bloodhound.tokenizers.whitespace,
          remote: {
            url: self.data.url + '?keyword=%QUERY',
            rateLimitWait: 200,
            wildcard: '%QUERY',
            transform: function(resp){
              usersCt = resp.users.length;
              return resp.users;
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
              header: function(){
                return '<h4> Teams </h4>';
              },
              suggestion: function(resp){
                return '<div><a href="/team/' + resp + '" data-navigo>' + resp + '</a></div>';
              },
              footer: function(resp){
                if (teamsCt > typeaheadLimit) {
                  return '<div class="tt-see-all"><a href="/query/' + Handlebars.escapeExpression(encodeURIComponent(resp.query)) + '/teams" data-navigo> See all ' + teamsCt + ' results for teams »</a></div>';
                }
              },
              empty: function(resp){
                return '<h4> No results found for "' + Handlebars.escapeExpression(resp.query) + '" </h4>';
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
              header: function(){
                return '<h4> Services </h4>';
              },
              suggestion: function(resp){
                return '<div><a href="/team/' + resp.team + '" data-navigo>' + resp.service + ' - ' + '<i>' + resp.team + '</i></a></div>';
              },
              footer: function(resp){
                if (servicesCt > typeaheadLimit) {
                  return '<div class="tt-see-all"><a href="/query/' + Handlebars.escapeExpression(encodeURIComponent(resp.query)) + '/services" data-navigo> See all ' + servicesCt + ' results for services »</a></div>';
                }
              }
            }
          },
          {
            name: 'users',
            hint: true,
            async: true,
            highlight: true,
            limit: typeaheadLimit,
            displayKey: 'name',
            source: users,
            templates: {
              header: function(){
                return '<h4> Users </h4>';
              },
              suggestion: function(resp){
                return '<div><a href="/dashboard/' + resp.name + '" data-navigo>' + resp.name + '</a></div>';
              },
              footer: function(resp){
                if (usersCt > typeaheadLimit) {
                  return '<div class="tt-see-all"><a href="/query/' + Handlebars.escapeExpression(encodeURIComponent(resp.query)) + '/users" data-navigo> See all ' + usersCt + ' results for users »</a></div>';
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
          .on('typeahead:selected', function(){
            var ttPath = $input.parents(self.data.searchForm).find('.tt-cursor a').attr('href');
            if (ttPath){
              router.navigate(ttPath);
            }
          });

        if (!query) {
          $input.trigger('focus');
        }
      });

    },
    events: function(){
      this.data.$page.on('submit', this.data.searchForm, this.updateSearch.bind(this));
      this.data.$page.on('click','.remove-card-column', this.deletePinnedTeam);
      router.updatePageLinks();
    },
    getData: function(query) {
      var param = {
            keyword: query.query
          };
      if (query.fields !== "all") {
        param.fields = query.fields;
      }

      $.get(this.data.url, param, this.renderResults.bind(this));
    },
    getTeamSummaries: function(){
      var self = this,
          pinned = this.data.pinnedTeams ? this.data.pinnedTeams : [],
          data = this.data.recentlyViewed ? this.data.recentlyViewed.concat(pinned) : pinned;

      if (data) {
        for (var i = 0; i < data.length; i++) {
          (function(i){
            var team = data[i],
                summaryUrl = self.data.summaryUrl + team + '/summary';
            $.get(summaryUrl).done(function(response){
              var model = {
                data: response,
                name: team
              };
              self.renderCardInner.call(self, model);
            }).fail(function(response){
              var model = {
                data: response,
                name: team
              };
              self.renderCardInner.call(self, model);
            });
          })(i);
        }
      }
    },
    renderPage: function(){
      var template = Handlebars.compile(this.data.pageSource);
      this.data.$page.html(template({recent: this.data.recentlyViewed, pinned: this.data.pinnedTeams}));
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
      var template = Handlebars.compile(this.data.searchResultsSource),
          serviceDisplayLimit = 5;
      if (data.services && data.teams && data.users && Object.keys(data.services).length === 0 && data.teams.length === 0 && data.users.length === 0) {
        // Mark object empty if not search results are returned
        data.noResults = true;
      }

      if (data.services && Object.keys(data.services).length) {
        // Transform result to collapse services by team
        var hash = {};
        for (var i = 0, key, item, keys = Object.keys(data.services); i < keys.length; i++) {
          item = data.services[keys[i]];
          key = keys[i];
          for (var j = 0; j < item.length; j++) {
            team = item[j];
            if (!hash[team]) {
              hash[team] = {
                total: 1,
                list: []
              };
              hash[team].list.push(key);
            } else {
              if (hash[team].list.length < serviceDisplayLimit) {
                hash[team].list.push(key);
              }
              hash[team].total++;
            }
          }
        }

        data.services = hash;
      }

      this.data.$page.find('.search-results').html(template(data));
      router.updatePageLinks();
    },
    deletePinnedTeam: function(e){
      var $teamCard = $(this).parents('.module-card'),
          $pinnedTeams = $('#pinned-teams'),
          teamName = $teamCard.attr('data-team');

      $.ajax({
        type: 'DELETE',
        url: 'api/v0/users/' + oncall.data.user + '/pinned_teams/' + teamName,
        dataType: 'html'
      }).done(function(){
        $teamCard.remove();
        if ($pinnedTeams.find('.module-card').length === 0) {
          $pinnedTeams.hide()
        }
      }).fail(function(data){
        var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Could not unpin team.';
        oncall.alerts.createAlert('Failed: ' + error, 'danger');
      });
    }
  },
  team: {
    data: {
      $page: $('.content-wrapper'),
      $pinButton: $('#pin-team'),
      url: '/api/v0/teams/',
      pinUrl: '/api/v0/users/',
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
      var url = this.data.url,
          $modalBody = $modal.find('.modal-body'),
          $cta = $modal.find('.modal-cta'),
          name = $form.find('#team-name').val().trim(),
          email = $form.find('#team-email').val(),
          description = $form.find('#team-description').val(),
          slack = $form.find('#team-slack').val(),
          slack_notifications = $form.find('#team-slack-notifications').val(),
          timezone = $form.find('#team-timezone').val(),
          $irisEnabled = $form.find('#team-iris-enabled'),
          model = {};

      $form.find(':input[type="text"]').each(function(){
        var $this = $(this);
        if ($this.val().length) {
          model[$this.attr('name')] = $this.val();
        }
      });
      model[$form.find('#team-timezone').attr('name')] = timezone;
      model[$irisEnabled.attr('name')] = $irisEnabled.prop('checked');

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
          description = $form.find('#team-description').val(),
          slack = $form.find('#team-slack').val(),
          slack_notifications = $form.find('#team-slack-notifications').val(),
          timezone = $form.find('#team-timezone').val(),
          overrideNumber = $form.find('#team-override-phone').val(),
          irisPlan = $form.find('#team-irisplan').val(),
          irisEnabled = $form.find('#team-iris-enabled').prop('checked'),
          model = {};

      $form.find(':input[type="text"]').not('.tt-hint').each(function(){
        var $this = $(this);
        model[$this.attr('name')] = $this.val();
      });
      model[$form.find('#team-timezone').attr('name')] = timezone;
      model[$form.find('#team-iris-enabled').attr('name')] = irisEnabled;

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
              description: description,
              slack_channel: slack,
              slack_channel_notifications: slack_notifications,
              scheduling_timezone: timezone,
              override_phone_number: overrideNumber,
              iris_plan: irisPlan,
              iris_enabled: irisEnabled ? '1' : '0',
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
      var $modalBody = $modal.find('.modal-body'),
          $cta = $modal.find('.modal-cta'),
          url = this.data.url + this.data.teamName,
          self = this;

      $cta.addClass('loading disabled').prop('disabled', true);

      $.ajax({
        type: 'DELETE',
        url: url,
        dataType: 'html'
      }).done(function(){
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
    pinTeam: function($modal) {
      var $cta = $modal.find('.modal-cta'),
          self = this;

      $cta.addClass('loading disabled').prop('disabled', true);
      $.ajax({
          type: 'POST',
          url: self.data.pinUrl + oncall.data.user + '/pinned_teams/',
          contentType: 'application/json',
          dataType: 'html',
          data: JSON.stringify({team:self.data.teamName})
        }).done(function(){
          oncall.alerts.removeAlerts();
          oncall.alerts.createAlert('Pinned team to home page', 'success');
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Pinning team failed.';
          oncall.alerts.createAlert(error, 'danger');
        }).always(function(){
        $cta.removeClass('loading disabled').prop('disabled', false);
        $modal.modal('hide');
        });
    },
    calendar: {
      data: {
        $page: $('.content-wrapper'),
        calendar: '#calendar-container',
        $calendar: null,
        url: '/api/v0/teams/',
        userUrl: '/api/v0/users/',
        pageSource: $('#team-calendar-template').html(),
        escalateModalTemplate: $('#team-escalate-modal'),
        cardColumnTemplate: $('#card-column-template').html(),
        cardInnerTemplate: $('#card-inner-slim-template').html(),
        cardOncallTemplate: $('#card-oncall-template').html(),
        addCardTemplate: $('#add-card-item-template').html(),
        calendarTypesTemplate: $('#calendar-types-template').html(),
        escalateModal: '#team-escalate-modal',
        escalatePlanSelect: '#escalate-plan',
        cardExtra: '.card-inner[data-collapsed]',
        cardExtraChevron: '.card-inner[data-collapsed] .svg-icon-chevron',
        oncallNowDisplayRoles: ['primary', 'secondary', 'manager'],
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
        };
        oncall.callbacks.onLogout = function(){
          self.checkIfAdmin();
          self.data.$calendar.incalendar('updateCalendarOption', 'user', null);
          self.data.$calendar.incalendar('updateCalendarOption', 'readOnly', true, true);
        }
      },
      events: function(){
        this.data.$page.on('click', this.data.cardExtraChevron, this.toggleCardExtra.bind(this));
        this.data.$page.on('change', this.data.escalatePlanSelect, this.updatePlanDescription.bind(this));
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
          };
          self.renderPage(data);
        });
      },
      getTeamSummary: function(){
        $.getJSON(this.data.url + this.data.teamName + '/summary', this.renderTeamSummary.bind(this));
      },
      renderPage: function(data){
        var template = Handlebars.compile(this.data.pageSource),
            self = this;

        self.data.$page.html(template(data));
        self.events();
        self.data.$calendar = $(self.data.calendar);
        // wait for user info data before creating calendar for timezone reasons
        $.when(oncall.data.rolesPromise, oncall.data.userInfoPromise).done(function(){
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
                  // #TODO: Fix after full name from API is sorted out. in the
                  // mean time, replaces the full name of the event with full
                  // name from teamData for display.
                  if (!evt.full_name && userData.full_name) {
                    evt.full_name = userData.full_name;
                  }
                  if (evt.full_name) {
                    self.data.$calendar.find('.inc-event[data-id="' + evt.id + '"]')
                                       .find('.inc-event-name')
                                       .text(evt.full_name);
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
              readOnly: oncall.data.user && Object.keys(self.data.teamData.users).indexOf(oncall.data.user) !== -1 ? false : true && oncall.data.userIsGod === 0,
              timezone: oncall.data.userTimezone,
              team: self.data.teamName,
              roles: oncall.data.roles
            }
          );
        });
      },
      checkIfAdmin: function(){
        var data = this.data.teamData;

        data.isAdmin = false;

        if (oncall.data.userIsGod === 1) {
          data.isAdmin = true;
        } else {
          for (var i in data.admins) {
            if (data.admins[i].name === oncall.data.user) {
              data.isAdmin = true;
            }
          }
        }

        this.data.$page.attr('data-admin', data.isAdmin);
      },
      renderTeamSummary: function(data){
        var template = Handlebars.compile(this.data.cardOncallTemplate),
            $container = this.data.$page.find('#oncall-now-container'),
            self = this,
            roles = oncall.data.roles;

        data.oncallNow = [];
        data.showEscalate = oncall.data.user && this.data.teamData.iris_enabled;

        // Sort data for oncall now module by display_order

        for (var i = 0, key, item, keys = Object.keys(data.current); i < keys.length; i++) {
          key = keys[i];
          item = data.current[key];
          if (this.data.oncallNowDisplayRoles.indexOf(key) !== -1) {
            data.oncallNow.push(item);
          }
        }

        data.oncallNow.sort(function(a,b){
          var roleA = roles.filter(function(item){
            return item.name === a[0].role;
          })[0];

          var roleB = roles.filter(function(item){
            return item.name === b[0].role;
          })[0];

          return roleA.display_order > roleB.display_order ? 1 : -1;
        });

        // Set first item in array to not be collapsed for UX

        if (data.oncallNow.length) {
          data.oncallNow[0][0].collapsed = false;
        }

        oncall.data.irisSettingsPromise.done(function(){
          data.showEscalate = data.showEscalate && oncall.data.irisSettings.activated;
          if (data.showEscalate) {
            data.custom_plan = self.data.teamData.iris_plan;
            data.urgent_plan = oncall.data.irisSettings.urgent_plan.name;
            data.medium_plan = oncall.data.irisSettings.medium_plan.name;
          }
          $container.html(template(data));
          self.setupEscalateModal();
        });
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

        $card.attr('data-collapsed', $card.attr('data-collapsed') !== "true");
      },
      renderEventUserDetails: function($modal, $calendar, $eventItem, evt) {
        // #TODO: Leverage this to create whole modal
        var $ul = $modal.find('.inc-event-details-view'),
            $title = $modal.find('.inc-event-details-title'),
            userData = this.data.teamData.users[evt.user],
            userPromise = $.Deferred(),
            self = this;

        if (userData !== undefined || $eventItem.attr('data-disabled') === '1') {
          userPromise.resolve();
        } else {
          $eventItem.attr('data-disabled', '1');
          $.ajax({
            type: 'GET',
            url: this.data.userUrl + evt.user,
            contentType: 'application/json',
            dataType: 'html'
          }).done(function(response){
            userData = JSON.parse(response);
            self.data.teamData.users[evt.user] = userData;
            userPromise.resolve();
          }).fail(function(){
            userPromise.reject();
          }).always(function(){
            $eventItem.attr('data-disabled', '0');
          })
        }
        userPromise.done(function() {
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
                .append('<span class="data-col">' + userData.contacts.slack + '</span>')
            );
          if (evt.schedule_id) {
            $ul.append(
              $('<li />')
                .append('<small>This event is auto generated by the scheduler</small>')
            );
          }
          if (evt.team !== self.data.teamName) {
            $ul.append(
              $('<li />')
                .append('<small>This is a subscription event from ' + evt.team + '</small>')
            );
          }
        });
      },
      updatePlanDescription: function() {
        var $modal = $(this.data.escalateModal),
            plan = $modal.find('#escalate-plan').find('option:selected').text(),
            $description = $modal.find('#escalate-plan-description');
        switch (plan){
          case oncall.data.irisSettings.urgent_plan.name:
            $description.html('<i>For urgent escalations. <b>WARNING: This will call the current on-call</b></i>');
            break;
          case oncall.data.irisSettings.medium_plan.name:
            $description.html('<i>For medium-priority escalations.</i>');
            break;
          case this.data.teamData.iris_plan:
            $description.html('<i>Escalate using this team\'s custom plan</i>');
            break;
        }

      },
      setupEscalateModal: function(){
        var $modal = $(this.data.escalateModal),
            $modalForm = $modal.find('.modal-form'),
            $modalBody = $modal.find('.modal-body'),
            $modalInput = $modalForm.find('.create-input'),
            $modalBtn = $modal.find('#escalate-btn'),
            $cta = $modal.find('.modal-cta'),
            self = this;

        this.updatePlanDescription();
        $modal.on('shown.bs.modal', function(){
          $modalInput.trigger('focus');
        });

        $modalBtn.on('click', function(e){
          $cta.addClass('loading disabled').prop('disabled', true);
          e.preventDefault();
          $modal.find('.alert').remove();

          $.ajax({
            type: 'POST',
            url: self.data.url + self.data.teamName + '/iris_escalate',
            contentType: 'application/json',
            dataType: 'html',
            data: JSON.stringify({description: $modalForm.find('#escalate-description').val(),
                                  plan: $modalForm.find('#escalate-plan').val()})
          }).done(function(response){
            $modal.modal('hide');
            oncall.alerts.removeAlerts();
            oncall.alerts.createAlert('Escalated incident to ' + self.data.teamName + ' successfully. <a href="'
              + oncall.data.irisSettings.api_host + '/incidents/' + response + '">See incident details.</a>', 'success');
          }).fail(function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Escalation failed.';
            oncall.alerts.createAlert(error, 'danger', $modalBody);
          }).always(function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
          });
        });

        $modal.on('hide.bs.modal', function(){
          $modal.find('.alert').remove();
          $modalForm[0].reset();
        });
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
        };
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
          data.services.sort();
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
          };
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
        var isInfoAdmin = false;

        data.isAdmin = false;
        if (oncall.data.userIsGod === 1) {
          data.isAdmin = true;
          isInfoAdmin = true;
        } else {
          for (var i in data.admins) {
            // if team api managed and user is not superadmin then disable editing of team info
            if (data.admins[i].name === oncall.data.user && !data.api_managed_roster) {
              data.isAdmin = true;
              isInfoAdmin = true;
            } else if (data.admins[i].name === oncall.data.user) {
              isInfoAdmin = true;
            }
          }
        }

        this.data.$page.attr('data-admin', data.isAdmin);
        this.data.$page.attr('info-admin', isInfoAdmin);
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
        }).done(function(){
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
          data = JSON.parse(data);

          if (roster === 'services') {
            $cardWrapper.append(pillTemplate(item));
          } else {
            var blankModel = {
              newItem: true,
              admin: roster === 'admins',
              user: data
            };

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
        }).done(function(){
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
            $card = $this.parents('.module-card'),
            roster = $card.attr('data-col-name'),
            user = $this.parents('.card-inner').attr('data-card-name'),
            url = this.data.url + this.data.teamName + '/rosters/' + roster + '/users/' + user,
            method = $this.attr('data-in-rotation') !== 'true';

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
    subscriptions: {
      data: {
        $page: $('.content-wrapper'),
        url: '/api/v0/teams/',
        subscriptionUrl: '/subscriptions',
        teamName: null,
        pageSource: $('#team-subscriptions-template').html(),
        moduleSubscriptionTemplate: $('#module-subscription-template').html(),
        moduleSubscriptionCreateTemplate: $('#module-subscription-create-template').html(),
        addSubscriptionItem: '#add-subscription',
        saveSubscription: '#save-subscription',
        addSubscriptionContainer: '.add-subscription-container',
        subscriptionCreateForm: '.module-subscription-create',
        moduleSubscriptionsWrapper: '.module-subscriptions-wrapper',
        deleteSubscriptionCard: '.delete-subscription-item',
        subscriptionItem: '.module-subscription',
        subscriptionCount: '.subscription-count'
      },
      init: function(name){
        Handlebars.registerPartial('module-subscription', this.data.moduleSubscriptionTemplate);
        Handlebars.registerPartial('module-subscription-create', this.data.moduleSubscriptionCreateTemplate);
        this.data.teamName = decodeURIComponent(name);
        this.getData();
      },
      events: function(){
        router.updatePageLinks();
        this.data.$page.on('click', this.data.addSubscriptionItem, this.addSubscriptionItem.bind(this));
        this.data.$page.on('submit', this.data.subscriptionCreateForm, this.saveSubscription.bind(this));
        this.data.$page.on('click', this.data.deleteSubscriptionCard, this.deleteSubscription.bind(this));
      },
      getData: function(){
        var template = Handlebars.compile(this.data.pageSource),
            self = this;

        $.when($.getJSON(this.data.url + this.data.teamName + this.data.subscriptionUrl),
          $.getJSON(this.data.url + this.data.teamName),
          oncall.data.rolesPromise).done(function(subData, teamData){
            data = teamData[0];
            data.subscriptions = subData[0];
            data.roles = oncall.data.roles;

            self.data.teamData = data;
            self.data.$page.html(template(data));
            self.events();
            self.renderSubscriptionCounts();
          }).fail(function(error){
          var data = {
            error: true,
            error_code: error.status,
            error_status: error.statusText,
            error_text: name + ' team not found'
          };
          self.data.$page.html(template(data));
        });
      },
      addSubscriptionItem: function(e){
        var template = Handlebars.compile(this.data.moduleSubscriptionCreateTemplate),
            $container = $(e.target).parents().find(this.data.addSubscriptionContainer),
            teamData = $.extend(true, {}, this.data.teamData);
        $container.prepend(template(teamData));
        oncall.typeahead.init();
      },
      saveSubscription: function(e){
        e.preventDefault();

        var self = this,
          $form = $(e.target),
          subscription = {},
          $cta = $form.find(this.data.saveSubscription),
          template = Handlebars.compile(this.data.moduleSubscriptionTemplate),
          url = this.data.url + this.data.teamName + this.data.subscriptionUrl,
          method = 'POST';

        subscription.subscription = $form.find('input.typeahead.tt-input.subscription-team').val();
        subscription.role = $form.find('.subscription-role').val();
        if (subscription.role === undefined || subscription.subscription === '') {
          oncall.alerts.createAlert('Invalid or missing field.');
        } else {
          oncall.alerts.removeAlerts();
          $.ajax({
            type: method,
            url: url,
            contentType: 'application/json',
            dataType: 'html',
            data: JSON.stringify(subscription)
          }).done(function () {
            self.data.$page.find(self.data.moduleSubscriptionsWrapper).append(template(subscription));
            $form.remove();
            self.renderSubscriptionCounts();
          }).fail(function (data) {
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Request failed.';
            oncall.alerts.createAlert(error, 'danger');
          }).always(function () {
            $cta.removeClass('loading disabled').prop('disabled', false);
          });
        }
      },
      deleteSubscriptionItem: function($modal, $caller){
        var $form = $caller.parents(this.data.subscriptionCreateForm);
        $form.remove();
        $modal.modal('hide');
      },
      deleteSubscription: function($modal, $caller) {
        var $card = $caller.parents('.module-card'),
            $modalBody = $modal.find('.modal-body'),
            $cta = $modal.find('.modal-cta'),
            role = $card.attr('data-role'),
            subscription = $card.attr('data-team'),
            url = this.data.url + this.data.teamName + '/subscriptions/' + subscription + '/' + role,
            self = this;

        $cta.addClass('loading disabled').prop('disabled', true);

        $.ajax({
          type: 'DELETE',
          url: url,
          dataType: 'html'
        }).done(function(){
          $modal.modal('hide');
          $card.remove();
          self.renderSubscriptionCounts();
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
          oncall.alerts.createAlert(error, 'danger', $modalBody);
        }).always(function(){
          $cta.removeClass('loading disabled').prop('disabled', false);
        });
      },
      renderSubscriptionCounts: function() {
        $(this.data.subscriptionCount).text($(this.data.moduleSubscriptionsWrapper).find(this.data.subscriptionItem).length);
      }
    },
    schedules: {
      data: {
        $page: $('.content-wrapper'),
        $calendar: null,
        addRotationItem: '.add-rotation-item',
        addScheduleContainer: '.add-schedule-container',
        addScheduleItem: '#add-schedule',
        calendar: '#calendar-container',
        deleteScheduleItem: '.delete-schedule-item',
        editScheduleItem: '.edit-schedule-item',
        events: [],
        moduleScheduleTemplate: $('#module-schedule-template').html(),
        moduleScheduleCreateTemplate: $('#module-schedule-create-template').html(),
        moduleScheduleWrapper: '.module-schedule-wrapper',
        moduleSchedule: '.module-schedule',
        pageSource: $('#team-schedules-template').html(),
        populateSchedulesModal: '#populate-schedule-modal',
        previewSchedule: '.preview-schedule',
        removeRotationItem: '.remove-rotation-item',
        rosterSelect: '.schedule-roster',
        rotationItem: '.rotation-item',
        rotationItemTemplate: $('#rotation-item-template').html(),
        saveSchedule: '#save-schedule',
        scheduler: '#schedule-algorithm',
        scheduleAdvanced: '.schedule-advanced',
        scheduleCard: '.module-schedule-create',
        scheduleCount: '.schedule-count',
        scheduleCreateForm: '.module-schedule-create',
        scheduleItem: '.module-card',
        schedulerTemplates: {
          'default': $('#default-scheduler-template').html(),
          'round-robin': $('#round-robin-scheduler-template').html(),
          'no-skip-matching': $('#allow-duplicate-scheduler-template').html(),
          'multi-team': $('#multi-team-template').html(),
        },
        schedulerTypeContainer: '.scheduler-type-container',
        schedulesUrl: '/api/v0/schedules/',
        teamName: null,
        toggleAdvanced: '.toggle-advanced',
        toggleScheduleView: '.toggle-schedule-view',
        url: '/api/v0/teams/',
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
        this.data.$page.on('change', this.data.scheduler, this.schedulerAlgo.bind(this));
        this.data.$page.on('change', this.data.rosterSelect, this.schedulerRoster.bind(this));
      },
      getData: function(name){
        var self = this,
            events = this.data.events,
            rows = 1,
            msPerMinute = 60 * 1000,
            msPerHour = msPerMinute * 60,
            msPerDay = msPerHour * 24,
            msPerWeek = msPerDay * 7;

        $.when($.getJSON(this.data.url + this.data.teamName),
          oncall.data.rolesPromise, oncall.data.timezonesPromise).done(function(data){
          // shim api response for calendar / modules
          data = data[0];
          for (var i in data.rosters) {
            if (data.rosters.hasOwnProperty(i)) {
              var item = data.rosters[i];
              for (var k = 0; k < item.schedules.length; k++) {
                var schedule = item.schedules[k];
                schedule.is_12_hr = !schedule.advanced_mode && schedule.events.length > 1;
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
          };
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
            item.duration = Handlebars.helpers.scaleSeconds(item.durationMs / 1000, 'duration');
            item.durationUnit = Handlebars.helpers.scaleSeconds(item.durationMs / 1000, 'unit');
          }
          if (data.advanced_mode === 0 && data.events.length > 1) {
            data.is_12_hr = true;
            data.events[0].totalEvents = data.events.length; // Since the UI only uses the first event to create the schedule card, we assign the total length of events so the UI knows if the event is weekly or biweekly
          }
          teamData.selected_schedule = data;
        }

        $container.prepend(template(teamData));
        this.renderSchedulerData();
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
            roster = $form.find(this.data.rosterSelect).val(),
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
            };
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
                };
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
              };
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
            scheduler = this.getSchedulerData.call(this, $form) || {},
            events = this.formatScheduleData($form),
            url = id ? this.data.schedulesUrl + id : this.data.url + this.data.teamName + '/rosters/' + roster + '/schedules',
            method = id ? 'PUT' : 'POST',
            submitModel = {
              timezone: 'US/Pacific',
              roster: roster,
              role: role,
              auto_populate_threshold: threshold,
              advanced_mode: advancedMode,
              scheduler: scheduler,
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
            };

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
              submitModel.is_12_hr = !submitModel.advanced_mode && submitModel.events.length > 1;
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
          }).done(function(){
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
        $this.attr('data-collapsed', $this.attr('data-collapsed') !== "true");
      },
      renderPopulateScheduleModal: function(){
        var self = this,
            $modal = $(self.data.populateSchedulesModal),
            $modalDate = $modal.find('#populate-schedule-date'),
            $modalThreshold = $modal.find('#populate-schedule-threshold'),
            $modalBtn = $modal.find('#populate-schedule-btn'),
            $previewBtn = $modal.find('#preview-schedule-btn'),
            $calContainer = $modal.find('#modal-calendar-container'),
            scheduleData,
            scheduleId,
            threshold,
            now = moment();

        $modal.on('shown.bs.modal', function(e){
          scheduleData = JSON.parse($(e.relatedTarget).parents(self.data.scheduleItem).attr('data-model'));
          scheduleId = scheduleData.id;
          threshold = scheduleData.auto_populate_threshold;

          $modal.find('#modal-calendar-container').data('incalendar', null).incalendar({
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

        $previewBtn.on('click', function(){
          var date = new Date($modalDate.val());

          if ( isNaN(Date.parse(date)) ) {
            oncall.alerts.createAlert('Invalid date.', 'danger', $modal.find('.modal-body'));
          } else {
            self.populatePreview(date.valueOf(), $(this), $modal);
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
            persistSettings: false,
            onEventGet: function(events, $cal){
              $cal.find('[data-schedule-id="' + scheduleId + '"]').attr('data-highlighted', true);
            },
            onEventAlways: function(){
            },
            onFetchFail: function(data){
            },
          });
        }).fail(function(data){
          var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Populate failed.';
          oncall.alerts.createAlert(error, 'danger', $modal.find('.modal-body'));
        }).always(function(){
          $cta.removeClass('loading disabled').prop('disabled', false);
        });
      },
      populatePreview: function(date, $cta, $modal){
        var date = (date || Date.now()) / 1000,
            self = this,
            $calContainer = $modal.find('#modal-calendar-container'),
            scheduleId = $modal.attr('data-schedule-id');

        $cta.addClass('loading disabled').prop('disabled', true);

        oncall.alerts.removeAlerts();
        $calContainer.data('incalendar', null).incalendar({
          eventsUrl: '/api/v0/schedules/'+ scheduleId+'/preview',
          getEventsUrl: '/api/v0/schedules/'+ scheduleId+'/preview?team__eq=' + self.data.teamName + '&start=' + date + '&teamName=' + self.data.teamName,
          readOnly: true,
          persistSettings: false,
          onEventGet: function(events, $cal){
            $cal.find('[data-schedule-id="' + scheduleId + '"]').attr('data-highlighted', true);
          },
          onEventAlways: function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
          },
          onFetchFail: function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Preview failed.';
            oncall.alerts.createAlert(error, 'danger', $modal.find('.modal-body'));
          },
        });
      },
      getSchedulerData: function($form) {
        // Function accepts form and returns an object with
        // formatted scheduler algorithm data based on algo selected
        var type = $form.find(this.data.scheduler).val(),
            schedulerData = {
              name: type,
              data: []
            };

        if (type === 'round-robin') {
          // if custom order is selected, send user list along with type
          $form.find('.round-robin-scheduler li').each(function(i){
            schedulerData.data.push($(this).data('user'));
          });
        }

        return schedulerData;
      },
      schedulerAlgo: function(e) {
        var $select = $(e.target),
            val = $select.val(),
            $card = $select.parents(this.data.scheduleCard);

        $card.attr('data-scheduler', val);
        this.renderSchedulerData($card);
      },
      schedulerRoster: function(e) {
        var $select = $(e.target),
            $card = $select.parents(this.data.scheduleCard);

        this.renderSchedulerData($card);
      },
      renderSchedulerData: function($card) {
        // Call this function to render scheduler-specific templates
        // The name-template map is defined under 'schedules.data.schedulerTemplates'
        var $card = $card || $(this.data.scheduleCard).first(),
            scheduler = $card.attr('data-scheduler') || 'default',
            source = this.data.schedulerTemplates[scheduler],
            template = Handlebars.compile(source),
            $container = $card.find(this.data.schedulerTypeContainer),
            roster = $card.find(this.data.rosterSelect).val();

        if ( scheduler === 'round-robin' ) {
          // Pass in user list to template if custom order is selected
          var schedule_id = $card.attr('data-edit-id'),
              order = $card.attr('data-schedule-data'),
              users = this.data.teamData.rosters[roster].users.map(function(user) {return user.name});
              schedule = this.data.teamData.rosters[roster].schedules.filter(function (schedule) {
                return schedule.id === parseInt(schedule_id)
              })[0];

          if (order !== undefined) {
            order = JSON.parse(order);
          }
          // If order includes all roster users, use order. Otherwise, just use roster
          if (order !== undefined && order.every(function(u) { return users.indexOf(u) !== -1})) {
            $container.html(template(order));
          } else {
            $container.html(template(users));
          }
          this.drag.init($container.find('.draggable'));
        } else {
          $container.html(template());
        }
      },
      drag: {
        data: {
          $draggedEl: null
        },
        init: function($el){
          var self = this;

          $el.on('dragstart','li', self.handleDragStart.bind(this));
          $el.on('dragend','li', self.handleDragEnd.bind(this));
          $el.on('drop', 'li', self.handleDrop.bind(this));
          $el.on('dragover', 'li', self.handleDragOver);
          $el.on('dragenter', 'li', self.handleDragEnter);
          $el.on('dragleave', 'li', self.handleDragLeave);

        },
        handleDragStart: function(e){
          e = e.originalEvent;
          e.stopPropagation();
          this.data.$draggedEl = $(e.target);
          $(e.target).addClass('dragging').parents('ul').addClass('drag-source');
          e.dataTransfer.effectAllowed = "move";
          e.dataTransfer.setData('text/html', e.target.outerHTML);
        },
        handleDragEnd: function(e){
          $(e.target).removeClass('dragging');
          $('.drag-source').removeClass('drag-source');
        },
        handleDragOver: function(e){
          e.preventDefault();
          $(this).addClass('drag-over');
          return false;
        },
        handleDragEnter: function(e){
          e.preventDefault();
          $(this).addClass('drag-over');
        },
        handleDragLeave: function(e){
          e.preventDefault();
          $(this).removeClass('drag-over');
        },
        handleDrop: function(e){
          var $this = $(e.currentTarget);

          e.preventDefault();
          e.stopPropagation();
          e = e.originalEvent;

          if(!$this.hasClass('drag-source')) {
            $this.after(e.dataTransfer.getData('text/html'));
            this.data.$draggedEl.remove();
          }
          $('.drag-over').removeClass('drag-over');
          $('.dragging').removeClass('dragging');
          $('.drag-source').removeClass('drag-source');
        }
      }
    },
    audit: {
      data: {
        $page: $('.content-wrapper'),
        url: '/api/v0/teams/',
        auditUrl: '/api/v0/audit',
        teamName: null,
        pageSource: $('#team-audit-template').html(),
      },
      init: function(name){
        var start_time = moment().subtract(30, 'days');
        this.data.teamName = decodeURIComponent(name);
        this.getData(start_time);
      },
      events: function(){
        var self = this;
        router.updatePageLinks();
        this.data.$page.on('click', '#refresh-audit-btn', function(){
          var date = new Date($('#audit-date').val());

          if ( isNaN(Date.parse(date)) ) {
            oncall.alerts.createAlert('Invalid date.', 'danger');
          } else {
            self.getData(moment(date.valueOf()));
          }
        });
      },
      formatAudit: function(audit) {
        audit['timestamp'] = moment(audit['timestamp'] * 1000).format('YYYY/MM/DD');
        audit['context'] = JSON.parse(audit['context']);
        oncall.team.audit.formatContext(audit['context']);
        audit['context'] = JSON.stringify(audit['context'], null, 2);
      },
      formatContext: function(context) {
        // Descend recursively into audit context, replacing timestamps with date strings
        if (typeof context !== 'object') {
          return;
        }
        for (var key in context) {
          if (context[key] == null){
            continue;
          } else if (key === 'start' || key === 'end') {
            context[key] = moment(context[key] * 1000).format('YYYY/MM/DD HH:mm')
          } else if (context[key].constructor === Array) {
            for (a in context[key]) {
              oncall.team.audit.formatContext(a);
            }
          } else if (typeof context[key] === 'object') {
            oncall.team.audit.formatContext(context[key])
          }
        }
      },
      getData: function(start){
        var template = Handlebars.compile(this.data.pageSource),
            self = this;

        $.when($.getJSON(this.data.auditUrl, {team: this.data.teamName, start: start.unix()}),
          $.getJSON(this.data.url + this.data.teamName)).done(function(auditData, teamData) {
            data = teamData[0];
            auditData[0].map(self.formatAudit);
            data.audits = auditData[0];
            self.data.$page.html(template(data));
            $('#audit-date').val(start.format('YYYY/MM/DD'));
            self.events();
            $('.audit-table').DataTable({pageLength: 25});
          }).fail(function(error){
          var data = {
            error: true,
            error_code: error.status,
            error_status: error.statusText,
            error_text: name + ' team not found'
          };
        });
      },
    }
  },
  settings: {
    data: {
      $page: $('.content-wrapper'),
      url: '/api/v0/users/',
      pageSource: $('#settings-template').html(),
      $form: '#user-settings-form',
      settingsSubheaderTemplate: $('#settings-subheader-template').html(),
      subheaderWrapper: '.subheader-wrapper',
      telmodes: ["call", "sms"]
    },
    init: function(){
      Handlebars.registerPartial('settings-subheader', this.data.settingsSubheaderTemplate);
      oncall.getModes();
      this.getData();
    },
    events: function(){
      router.updatePageLinks();
      this.data.$page.on('submit', this.data.$form, this.updateSettings.bind(this));
    },
    getData: function(){
      if (oncall.data.user) {
        $.get(this.data.url + oncall.data.user, this.renderPage.bind(this));
      } else {
        router.navigate('/');
      }
    },
    renderPage: function(data){
      $.when(
        oncall.data.modesPromise
      ).done(function() {
        let contactModes = [];

        for(let key in data.contacts)
        {
          contactModes.push({
            label: key.substr(0, 1).toUpperCase() + key.substr(1),
            mode: key,
            value: data.contacts[key]
          });
        }
        data.contactmodes = contactModes;
      });
      var template = Handlebars.compile(this.data.pageSource),
           self = this;
      oncall.data.timezonesPromise.done(function() {
        data.timezones = oncall.data.timezones;
        data.telmodes = self.data.telmodes;
        self.data.$page.html(template(data));
        self.events();
      });
    },
    updateSettings: function(e){
      e.preventDefault();
      var $form = $(e.target),
          $cta = $form.find('button[type="submit"]'),
          url = this.data.url + oncall.data.user,
          data = $form.find('select[name="time_zone"]').val();
          userContactsElements = this.data.$form + ' input[type=text][name^="contactmode-"]';
          userContacts = {};

      $(userContactsElements).each(function(){
        let mode = $( this ).attr('id');
        userContacts[mode] = $( this ).val();
      });

      $cta.addClass('loading disabled').prop('disabled', true);

      $.ajax({
        type: 'PUT',
        url: url,
        dataType: 'html',
        contentType: 'application/json',
        data: JSON.stringify({contacts: userContacts, time_zone: data})
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
        oncall.getModes();
        oncall.multiSelect.init();
      },
      events: function(){
        router.updatePageLinks();
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
            $.get(this.data.typesUrl),
            oncall.data.rolesPromise,
            oncall.data.modesPromise
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
            notificationData.name = oncall.data.user; // using key `name` instead of `username` here because thats what API returns for /users
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
        $container.html(template(notificationData));
      },
      addReminder: function(e, data){
        var template = Handlebars.compile(this.data.moduleNotificationCreateTemplate),
            $container = $(e.target).parents().find(this.data.reminderCreateContainer),
            notificationData = this.data.notificationData;

        notificationData.selected = data;
        notificationData.createType = 'reminder';
        $container.html(template(notificationData));
      },
      formatNotificationData: function($form){
        var type = $form.data('type'),
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
          }).done(function(){
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
    },
    ical_key: {
      data: {
        $page: $('.content-wrapper'),
        url: '/api/v0/users/',
        icalKeyUrl: '/api/v0/ical_key/',
        pageSource: $('#ical-key-template').html(),
        settingsSubheaderTemplate: $('#settings-subheader-template').html(),
        moduleIcalKeyTemplate: $('#module-ical-key-template').html(),
        moduleIcalKeyCreateTemplate: $('#module-ical-key-create-template').html(),
        icalKeyCreateForm: '.module-ical-key-create',
        icalKeyCreateCancel: '.ical-key-create-cancel',
        icalKeyUserCreateContainer: '.ical-key-user-create-container',
        icalKeyTeamCreateContainer: '.ical-key-team-create-container',
        subheaderWrapper: '.subheader-wrapper',
        icalKeyRow: '.ical-key-row',
        createIcalKeyUser: '#create-ical-key-user',
        createIcalKeyTeam: '#create-ical-key-team'
      },
      init: function(){
        Handlebars.registerPartial('settings-subheader', this.data.settingsSubheaderTemplate);
        Handlebars.registerPartial('ical-key', this.data.moduleIcalKeyTemplate);
        this.getData();
      },
      events: function(){
        router.updatePageLinks();
        this.data.$page.on('submit', this.data.icalKeyCreateForm, this.createIcalKey.bind(this));
        this.data.$page.on('click', this.data.icalKeyCreateCancel, this.createIcalKeyCancel.bind(this));
        this.data.$page.on('click', this.data.createIcalKeyUser, this.createIcalKeyUser.bind(this));
        this.data.$page.on('click', this.data.createIcalKeyTeam, this.createIcalKeyTeam.bind(this));
      },
      getData: function(){
        var self = this;

        var icalKeyData = {
          userKeys: [],
          teamKeys: [],
          name: oncall.data.user,
          teams: []
        };
        this.data.icalKeyData = icalKeyData;

        if (oncall.data.user) {
          $.when(
            $.get(this.data.icalKeyUrl + 'requester/' + oncall.data.user),
            $.get(this.data.url + oncall.data.user + '/teams')
          ).done(function(icalKeys, teamsData){
            icalKeys = icalKeys[0];
            for (var i = 0; i < icalKeys.length; i++) {
              icalKeys[i].time_created = moment(icalKeys[i].time_created * 1000).format('YYYY/MM/DD HH:mm');
              if (icalKeys[i].type === 'user')
                icalKeyData.userKeys.push(icalKeys[i]);
              else if (icalKeys[i].type === 'team') {
                icalKeyData.teamKeys.push(icalKeys[i]);
              }
            }

            icalKeyData.teams = teamsData[0];

            self.renderPage.call(self, icalKeyData);
          }).fail(function(){
            // we need to handle failure because icalKeys promise return 404 when no key exists
            self.renderPage.call(self, icalKeyData);
          });
        } else {
          router.navigate('/');
        }
      },
      renderPage: function(data){
        var template = Handlebars.compile(this.data.pageSource);

        this.data.$page.html(template(data));
        this.events();
      },
      createIcalKeyUser: function(e, data){
        var template = Handlebars.compile(this.data.moduleIcalKeyCreateTemplate),
            $container = $(e.target).parents().find(this.data.icalKeyUserCreateContainer);

        var userCreateData = {
          createType: 'user',
          icalKeyOptions: [this.data.icalKeyData.name]
        };
        $container.html(template(userCreateData));
      },
      createIcalKeyTeam: function(e, data){
        var template = Handlebars.compile(this.data.moduleIcalKeyCreateTemplate),
            $container = $(e.target).parents().find(this.data.icalKeyTeamCreateContainer);

        var teamCreateData = {
          createType: 'team',
          icalKeyOptions: this.data.icalKeyData.teams
        };
        $container.html(template(teamCreateData));
      },
      createIcalKey: function(e){
        e.preventDefault();

        var self = this,
            $form = $(e.target),
            $cta = $form.find('.ical-key-create-save'),
            createType = $form.data('type'),
            // we cannot trim the name here because there are team names ending in space
            createName = $form.find('.ical-key-create-name').val(),
            url = this.data.icalKeyUrl + createType + '/' + createName;

        if ((createType === 'user' || createType === 'team') && createName) {
          $cta.addClass('loading disabled').prop('disabled', true);

          $.ajax({
            type: 'POST',
            url: url,
            dataType: 'html'
          }).done(function(data){
            $form.remove();
            self.getData();
          }).fail(function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
            oncall.alerts.createAlert(error, 'danger');
          }).always(function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
          });
        }
      },
      createIcalKeyCancel: function(e, $caller){
        var $form = $(e.target).parents(this.data.icalKeyCreateForm);
        $form.remove();
      },
      updateIcalKey: function($modal, $caller){
        var self = this,
            $cta = $modal.find('.modal-cta'),
            ical_type = $caller.attr('data-ical-type'),
            ical_name = $caller.attr('data-ical-name'),
            url = this.data.icalKeyUrl + ical_type + '/' + ical_name;

        if ((ical_type === 'user' || ical_type === 'team') && ical_name) {
          $cta.addClass('loading disabled').prop('disabled', true);

          $.ajax({
            type: 'POST',
            url: url,
            dataType: 'html'
          }).done(function(data){
            $modal.modal('hide');
            self.getData();
          }).fail(function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
            oncall.alerts.createAlert(error, 'danger');
          }).always(function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
          });
        } else {
          $modal.modal('hide');
        }
      },
      deleteIcalKey: function($modal, $caller){
        var self = this,
            $cta = $modal.find('.modal-cta'),
            key = $caller.attr('data-ical-key'),
            url = this.data.icalKeyUrl + 'key/' + key;

        if (key) {
          $cta.addClass('loading disabled').prop('disabled', true);

          $.ajax({
            type: 'DELETE',
            url: url,
            dataType: 'html'
          }).done(function(){
            $modal.modal('hide');
            self.getData();
          }).fail(function(data){
            var error = oncall.isJson(data.responseText) ? JSON.parse(data.responseText).description : data.responseText || 'Delete failed.';
            oncall.alerts.createAlert(error, 'danger');
          }).always(function(){
            $cta.removeClass('loading disabled').prop('disabled', false);
          });
        } else {
          $modal.modal('hide');
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
      }).on('shown.bs.modal', function(){
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
          $teamSlackNotifications = $modalForm.find('#team-slack-notifications'),
          $teamTimezone = $modalForm.find('#team-timezone'),
          $teamDescription = $modalForm.find('#team-description'),
          $teamNumber = $modalForm.find('#team-override-phone'),
          $teamIrisPlan = $modalForm.find('#team-irisplan'),
          $teamIrisEnabled = $modalForm.find('#team-iris-enabled'),
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
        $teamSlackNotifications.val($btn.attr('data-modal-slack-notifications'));
        $teamDescription.val($btn.attr('data-modal-description'));
        $teamNumber.val($btn.attr('data-modal-override-phone'));
        $teamIrisPlan.val($btn.attr('data-modal-irisplan'));
        $teamIrisEnabled.prop('checked', $btn.attr('data-modal-iris-enabled') === '1');
        $planInput = $('#team-irisplan');

        results = new Bloodhound({
          datumTokenizer: Bloodhound.tokenizers.obj.whitespace('value'),
          queryTokenizer: Bloodhound.tokenizers.whitespace,
          remote: {
            url: oncall.data.irisSettings.api_host + oncall.data.irisSettings.plan_url
              + '?name__startswith=%QUERY&fields=name',
            wildcard: '%QUERY'
          }
        });
        $planInput.typeahead('destroy');
        $planInput.typeahead(null, {
          hint: true,
          async: true,
          highlight: true,
          source: results,
          display: 'name',
          templates: {
            empty: '<div>&nbsp; No plans found. </div>'
          }
        }).on('typeahead:select', function(){
          $(this).attr('value', $(this).val());
        });

        if ($btn.attr('data-modal-timezone')) {
          $teamTimezone.val($btn.attr('data-modal-timezone'));
        }
      }).on('shown.bs.modal', function(){
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

    Handlebars.registerHelper('isGreaterThan', function(val1, val2, opts){
      return val1 > val2 ? opts.fn(this) : opts.inverse(this);
    });

    Handlebars.registerHelper('isLessThan', function(val1, val2, opts){
      return val1 < val2 ? opts.fn(this) : opts.inverse(this);
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

    Handlebars.registerHelper('capitalize', function(str){
      return str.charAt(0).toUpperCase() + str.slice(1);
    });

    Handlebars.registerHelper('friendlyScheduler', function(str){
      if (str ==='no-skip-matching') {
        return 'Default (allow duplicate)';
      } else if (str ==='multi-team') {
        return 'Default (multi-team aware)';
      }
      return str;
    });

    //takes a photo_url and if null retuns the default blank headshot-blank
    Handlebars.registerHelper('defaultPhoto', function(src){
      // removes hash tag from string
        return src || "/static/images/headshot-blank.jpg";
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
        //if a photo_url is requested return blank headshot instead of Unknown
        if(key=='photo_url')
        {
          return users[user.name][key] || "/static/images/headshot-blank.jpg";
        }
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
        alert = '<div id="' + this.data.alertId + '" class="alert ' + fixed + '" role="alert"><button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button><span class="alert-content"></span></div>';
        $el[action](alert);
      }

      $('#' + this.data.alertId)
      .removeClass(function(i, className){
        return (className.match (/(^|\s)alert-\S+/g) || []).join(' ');
      })
      .addClass('alert-' + type)
      .find('.alert-content').html(alertText);
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

        if (type === 'services' || type === 'teams') {
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
      this.data.$page.off('click.multiSelect').on('click.multiSelect', this.data.overlay, this.toggleOptions.bind(this));
      this.data.$page.off('change.multiSelect').on('change.multiSelect', this.data.options + ' input[type="checkbox"]', this.updateSelectVal.bind(this));
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
};

oncall.init();
