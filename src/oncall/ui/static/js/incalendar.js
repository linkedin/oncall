/* [IN]Calendar */

;(function ($, window, document, undefined) {
  var pluginName = "incalendar",
      defaults = {
          controls: ['month', 'week'],
          currentView: 'month',
          currentViewRoles: null,
          days: ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
          daysShort: ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'],
          dateFormat: 'YYYY/M/D',
          datePickerClass: 'inc-date-picker',
          displayDateFormat: 'M/D/YYYY',
          displayTimeFormat: 'HH:mm',
          drag: true,
          events: null,
          eventHeight: 22,
          eventTypes: [],
          firstDay: 0,
          modalWidth: 400,
          months: ['January','February','March','April','May','June','July','August','September','October','November','December'],
          monthsShort: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
          persistSettings: true, // save and retrieve settings to and from local storage
          rowCount: 2,
          readOnly: false,
          roles: [
            {'name': 'primary', 'display_order': 1},
            {'name': 'secondary', 'display_order': 2},
            {'name': 'vacation', 'display_order': 3}
          ],
          roleOrder: {},
          startDate: moment(),
          swapEvents: null, // #FIXME: swapevents shouldnt live in options
          timeFormat: 'HH:mm',
          today: moment(),
          toolbar: true,
          timezone: null,
          team: null,
          user: null,
          onInit: function (pluginInstance) {
            // callback for when calendar is initialized
          },
          onRender: function ($calendar) {
            // callback for when calendar render is completed
          },
          onEventGet: function (data, $calendar) {
            // callback for when fetch events ajax call is completed. list of events from server is passed in as arg
          },
          onEventAlways: function(){
            // callback for when fetch events ajax call is completed run regardless of success or failure
          },
          onFetchFail: function(data){
            // callback for when fetch calendar events fails
          },
          onAddEvents: function (events) {
            // callback for when events are added to calendar
          },
          onRemoveEvent: function () {
            // callback for when event is deleted from calendar
          },
          onModalOpen: function ($modal, $calendar, $eventItem, evt) {
            // callback for when any modal is opened
          },
          onModalClose: function ($modal, $calendar) {
            // callback for when any modal is closed
          },
          onEventDetailsModalOpen: function($modal, $calendar, $eventItem, evt) {
            // callback for when event details modal is opened
          },
          onEventDetailsModalClose: function($modal, $calendar) {
            // callback for when event details modal is closed
          },
          onEventMouseover: function ($element, evt) {
            // callback for when event is highlighted
          },
          onEventMouseout: function ($element, evt) {
            // callback for when mouse leaves event
          },
          onEventClick: function (evt, e) {
            // callback for when event is clicked
          }
      }

  function InCalendar (el, options) {

    if (defaults.persistSettings && options.persistSettings !== false) {
      // Independently load local storage options and merge them to default before loading options passed by user. This is to maintain order of priority.
      // Priority: default options -> local storage options -> options passed in at calendar init.
      this.localStorageService.init();
      defaults = $.extend( {}, defaults, this.localStorageService.settings );
    }

    this.$el = $(el);
    this.options = $.extend( {}, defaults, options );
    this.options.today = this._createMoment(this.options.today);
    this.options.startDate = this._createMoment(this.options.startDate);
    // set current view roles to match roles if no options are passed in and
    // no local storage data is found
    if (!this.options.currentViewRoles) {
      this.options.currentViewRoles = [];
      for (var i = 0; i < this.options.roles.length; i++) {
          var roleEntry = this.options.roles[i];
          this.options.currentViewRoles.push(roleEntry.name);
          this.options.roleOrder[roleEntry.name] = roleEntry.display_order;
      }
    } else {
      for (var i = 0; i < this.options.roles.length; i++) {
          var roleEntry = this.options.roles[i];
          this.options.roleOrder[roleEntry.name] = roleEntry.display_order;
      }
    }
    this._defaults = defaults;
    this._name = pluginName;
    this.init();
  }

  InCalendar.prototype = {
    init: function () {
      this.render();
      this.options.onInit.call(this, this);
    },
    render: function (date) {
      this.rowSlots = [];
      this.$el.empty();
      if (this.options.toolbar) {
        this.$el.append(this._buildToolbar(date));
      }
      this.$calendar = this._buildCalendar(date);
      this.$el.append(this.$calendar);
      if (this.options.drag) {
        this._dragEventHandlers(this.$el.find('.inc-node'));
      }
      if (this.options.events) {
        this.refreshCalendarEvents();
      }
      if (this.options.getEventsUrl) {
        this._fetchCalendarEvents();
      }
      if (this.options.persistSettings) {
        this.localStorageService.addSetting('currentView', this.options.currentView);
      }
      this.datePicker();
      this.options.onRender(this.$el);
    },
    _createMoment: function (date, format) {
      // date can be moment object or string with matching format passed in.
      // See http://momentjs.com/docs/#/parsing/string-format/
      // tz optional, will create the date under specified TZ. TZ data is managed in moment-tz-data.js
      var format = format || this.options.dateFormat + ' ' + this.options.timeFormat;

      if (this.options.timezone) {
        if (typeof(moment.tz) === 'undefined') {
          console.error('Requires moment.js and moment-timezone.js to apply timezone values');
        }
        if (format === 'x' || format === 'X') {
          // if date format is unix, create a unit based date then shift
          // timezone, otherwise create the date with timezone offset
          return moment(date, format).tz(this.options.timezone);
        }
        return moment.tz(date, format, this.options.timezone);
      } else {
        return moment(date, format);
      }
    },
    _buildToolbar: function (date, view, controls, todayBtn) {
      var self = this,
          $calTitle = $('<div class="inc-toolbar-title" />'),
          $controlLi,
          $controlUl = $('<ul class="inc-toolbar-controls" />'),
          $element = $('<div class="inc-toolbar" />'),
          controls = controls || self.options.controls,
          controlType,
          dayTitle = 'Day',
          date = date || self.options.startDate,
          months = self.options.months,
          monthsShort = self.options.monthsShort,
          monthTitle = months[date.month()] + ' ' + date.year(),
          todayBtn = todayBtn || true,
          view = view || self.options.currentView,
          weekRange = self.getWeekRange(date),
          weekTitle = monthsShort[weekRange.startDate.month()] + ' ' + weekRange.startDate.date() + ' - ' + monthsShort[weekRange.endDate.month()] + ' ' + weekRange.endDate.date() + ', ' + date.year();

      for (var i = 0; i < controls.length; i++) {
        controlType = controls[i];
        (function (controlType) {
          $controlUl
            .append( $('<li class="inc-toolbar-control" />')
              .addClass(function(){
                return view === controlType ? 'active' : '';
              })
              .attr('data-mode', controlType)
              .text(controlType)
              .click(function(){
                self.options.currentView = controlType;
                self.render();
              })
            )
        })(controlType);
      }

      $element
        .append( $controlUl )
        .append( $calTitle
          .append( $('<span class="inc-controls-title" />')
            .text(
              function () {
                if (view === 'day') {
                  return dayTitle;
                } else if (view === 'week') {
                  return weekTitle;
                } else {
                  return monthTitle;
                }
              }
            )
            .append('<i class="loader loader-small"></i>')
          )
          .prepend( $('<span class="inc-controls-prev" data-type=' + view + ' />')
            .html('<i class="inc-icon icon-chevron icon-chevron-left"><svg xmlns="http://www.w3.org/2000/svg" width="16px" height="16px" viewBox="0 0 10 8" style="fill: currentColor; opacity: .7;"><path d="M4 0l-4 4 4 4 1.5-1.5-2.5-2.5 2.5-2.5-1.5-1.5z" transform="translate(1)" /></svg></i>')
            .click(function () {
              self.stepCalendar('backward', view);
            })
          )
          .append( $('<span class="inc-controls-next" data-type=' + view + ' />')
            .html('<i class="inc-icon icon-chevron icon-chevron-right"><svg xmlns="http://www.w3.org/2000/svg" width="16px" height="16px" viewBox="0 0 10 8" style="fill: currentColor; opacity: .7;"><path d="M1.5 0l-1.5 1.5 2.5 2.5-2.5 2.5 1.5 1.5 4-4-4-4z" transform="translate(1)" /></svg></i>')
            .click(function () {
              self.stepCalendar('forward', view);
            })
          )
          .append(
            function () {
              if (todayBtn) {
                return $('<button id="inc-controls-today" class="btn btn-blue">Today</button>')
                        .click(function () {
                          if(moment().isAfter(self.options.today, 'day')){
                            location.reload();
                          }
                          else{
                            self.stepToDate(self.options.today);
                          }
                        });
              }
            }
          )
        );

      return $element;
    },
    _buildCalendar: function (date, view, rowCount, shortDayDisplay, nodeClass) {
      var self = this,
          days = shortDayDisplay ? self.options.daysShort : self.options.days,
          date = date || self.options.startDate,
          today = self.options.today,
          monthLength = self.daysInMonth(date),
          view = view || self.options.currentView,
          $calendar = $('<table class="inc-calendar" />'),
          $head = $('<thead class="inc-header" />'),
          $body = $('<tbody class="inc-body" />'),
          nodeClass = nodeClass || 'inc-node',
          colCount = days.length,
          prevMonthDate,
          nextMonthDate,
          firstDay = self.getFirstDay(date),
          lastDay = self.getLastDay(date),
          weekRange = self.getWeekRange(date),
          rowCount = rowCount || self.options.rowCount,
          day = 1,
          calArray = [],
          prevMonthArray = [],
          nextMonthArray = [];

      function buildMonthCalendar () {
        var $bodyTr,
            $el = $('<div class="inc-row inc-month-row" />'),
            headStr = '', // using string concat instead of append for perf.
            bodyStr = '';

        rowCount = Math.ceil( (firstDay + monthLength) / colCount );

        // build header
        for (var i = 0; i < colCount; i++) {
          headStr += '<th class="inc-month-header">' + days[i] + '</th>';
        }

        $el.append(
          $('<table />')
          .append(
            $('<thead />')
            .html(headStr)
          )
        ).appendTo($head);

        // build body
        for (var i = 0; i < rowCount; i++) {
          $el = $('<div class="inc-row inc-month-row" />');
          bodyStr = '';
          // create Calendar array for current/previous/next months
          calArray[i] = [];
          prevMonthArray[i] = [];
          nextMonthArray[i] = [];

          for(var j = 0, k = 1; j < colCount; j++) {
            if (i === 0) {
              if (j === firstDay) {
                //first day of the current month
                firstDay++;
                calArray[i][j] = day++;
              } else {
                // backfill last month
                // create new date for prev month
                prevMonthDate = date.clone().startOf('month').subtract(firstDay - j, 'days');
                prevMonthArray[i][j] = prevMonthDate.date();
              }
            } else if ( day <= monthLength ) {
              calArray[i][j] = day++;
            } else {
              if (!nextMonthDate) {
                nextMonthDate = date.clone().add(1, 'month');
              }
              nextMonthArray[i][j] = k++
            }
            if (prevMonthArray[i][j]) {
              bodyStr += '<td class="' + nodeClass + ' inc-day inc-day-out prev-month-day" data-date="' + prevMonthDate.format('YYYY/M/') + prevMonthArray[i][j] + '" data-time="00:00" data-day=' + self.options.daysShort[j].toLowerCase() + '>' + prevMonthArray[i][j] + '</td>';
            } else if (nextMonthArray[i][j]) {
              bodyStr += '<td class="' + nodeClass + ' inc-day inc-day-out prev-month-day" data-date="' + nextMonthDate.format('YYYY/M/') + nextMonthArray[i][j] + '" data-time="00:00" data-day=' + self.options.daysShort[j].toLowerCase() + '>' + nextMonthArray[i][j] + '</td>';
            } else {
              bodyStr += '<td class="' + nodeClass + ' inc-day' + ( date.clone().date(calArray[i][j]).isSame(today, 'd') ? ' today' : '') + '" data-date="' + date.format('YYYY/M/') + calArray[i][j] + '" data-time="00:00" data-day=' + self.options.daysShort[j].toLowerCase() + '>' + calArray[i][j] + '</td>';
            }
          }

          $el.append(
            $('<table />')
            .append(
              $('<tbody />')
              .append(
                $('<tr />')
                .html(bodyStr)
              )
            )
          ).appendTo($body);
        }
      }

      function buildWeekCalendar (date) {
        var $el = $('<div class="inc-row inc-week-row" />'),
            headStr = '', // using string concat instead of append for perf.
            bodyStr = '',
            weekColCt = 24,
            startDate = weekRange.startDate,
            endDate = weekRange.endDate;

        // build header
        headStr += '<th class="inc-week-day" data-cal-type="week">Hour</th>';
        for (var i = 0; i < weekColCt; i++) {
          headStr += '<th class="inc-week-header" data-cal-type="week">' + i + '</th>';
        }
        $el.append(
          $('<table />')
          .append(
            $('<thead />')
            .html(headStr)
          )
        ).appendTo($head);

        // build body
        for (var i = 0; i < colCount; i++) {
          $el = $('<div class="inc-row inc-week-row" />').addClass(function(){ return today.isSame(startDate, 'd') ? 'today': '' });
          bodyStr = '<td class="inc-week-day">' + days[i] + '<br />' + startDate.format('M/D/YYYY') + '</td>';

          for(var j = 0, k = 1; j < weekColCt; j++) {
            bodyStr += '<td class="' + nodeClass + ' inc-week-hour ' + (today.isSame(startDate.clone().hour(j), 'h') ? 'current-hour' : '') + '" data-date="' + startDate.format('YYYY/M/D') + '" data-time="' + (j < 10 ? '0' + j : j) + ':00"></td>';
          }

          $el.append(
            $('<table />')
            .append(
              $('<tr />')
              .html(bodyStr)
            )
          ).appendTo($body);
          startDate.add(1, 'day');
        }
      }

      function buildTemplateCalendar () {
        var $el = $('<div class="inc-row inc-month-row" />'),
            headStr = '',
            bodyStr = '';

        // build header
        for (var i = 0; i < colCount; i++) {
          headStr += '<th class="inc-month-header">' + days[i] + '</th>';
        }

        $el.append(
          $('<table />')
          .append(
            $('<thead />')
            .html(headStr)
          )
        ).appendTo($head);


        // build body
        for (var i = 0; i < rowCount; i++) {
          $el = $('<div class="inc-row inc-month-row" />');
          bodyStr = '';
          for (var j = 0; j < colCount; j++) {
            bodyStr += '<td class="' + nodeClass + ' inc-day" data-day="' + self.options.daysShort[j].toLowerCase() + '"></td>';
          }

          $el.append(
            $('<table />')
            .append(
              $('<tbody />')
              .append(
                $('<tr />')
                .html(bodyStr)
              )
            )
          ).appendTo($body);
        }
      }

      //render type of calendar
      if (view === 'week') {
        buildWeekCalendar();
      } else if (view === 'template') {
        buildTemplateCalendar();
      } else {
        buildMonthCalendar();
      }

      $calendar
      .attr('data-view', view)
      .attr('data-read-only', self.options.readOnly)
      .append($head)
      .append($body);

      return $calendar;
    },
    addCalendarRows: function (count, nodeClass) {
      var self = this,
          $body = self.$calendar.find('.inc-body'),
          nodeClass = nodeClass || 'inc-node',
          colCount = self.options.days.length,
          count = count || 1,
          $el = $('<div class="inc-row inc-month-row" />'),
          bodyStr = '';

      for (var i = 0; i < count; i++) {
        $el = $('<div class="inc-row inc-month-row" />');
        bodyStr = '';

        for (var j = 0; j < colCount; j++) {
          bodyStr += '<td class="' + nodeClass + ' inc-day" data-day="' + self.options.daysShort[j].toLowerCase() + '"></td>';
        }

        $el.append(
          $('<table />')
          .append(
            $('<tbody />')
            .append(
              $('<tr />')
              .html(bodyStr)
            )
          )
        ).appendTo($body);
      }
    },
    stepCalendar: function (direction) {
      var view = this.options.currentView,
          dir = direction || 'forward',
          method = dir === 'forward' ? 'add' : 'subtract';

      this.options.startDate[method](1, view);
      this.render();
    },
    stepToDate: function (date)  {
      this.options.startDate = date.clone();
      this.render();
    },
    daysInMonth: function (date) {
      var date = date || this.options.today;
      return date.daysInMonth();
    },
    getFirstDay: function (date) {
      var date = date || this.options.today;
      return date.clone().startOf('month').day();
    },
    getLastDay: function (date) {
      var date = date || this.options.today;
      return date.clone().endOf('month').day();
    },
    getCalStartDate: function () {
      return this._createMoment(this.$calendar.find('.inc-node:first').attr('data-date') + ' 00:00');
    },
    getCalEndDate: function () {
      return this._createMoment(this.$calendar.find('.inc-node:last').attr('data-date') + ' 24:00');
    },
    getCalStartVal: function () {
      return this.getCalStartDate().valueOf();
    },
    getCalEndVal: function () {
      return this.getCalEndDate().valueOf();
    },
    getCalRowCount: function () {
      return this.$calendar.find('.inc-body .inc-row').length;
    },
    getWeekRange: function (date) {
      var date = date || this.options.today,
          day = date.day(),
          startDate = date.clone().startOf('week'),
          endDate = date.clone().endOf('week');

      return {
        startDate: startDate,
        endDate: endDate
      }
    },
    getEventsWithinRange: function (start, end, role) {
      var result = [];

      for (var i = 0; i < this.options.events.length; i++) {
        var item = this.options.events[i];

        if ( item.end > start && item.start < end) {
          if (!role) {
            result.push(item);
          } else if (role === item.role) {
            result.push(item);
          }
        }
      }

      return result;
    },
    getCalendarOption: function (option) {
      return this.options[option];
    },
    getDSTOffset: function (ev) {
      var isStartDST = ev.startDateObj.isDST(),
          isEndDST = ev.endDateObj.isDST();
      // checks event start and end to return the offset for daylight savings time in hours
      if (isStartDST && !isEndDST) {
        return -1;
      } else if (!isStartDST && isEndDST) {
        return 1;
      } else {
        return null;
      }
    },
    updateCalendarUser: function (user) {
      this.options.user = user;
    },
    updateCalendarTeam: function (team) {
      this.options.team = team;
    },
    updateCalendarOption: function (option, val, refresh) {
      this.options[option] = val;
      if (refresh) {
        this.render();
      }
    },
    updateDisplayedEvents: function (eventTypes) {
      this.updateCalendarOption('currentViewRoles', eventTypes);
      this.$calendar.find('.inc-event').each(function(){
        var $this = $(this);

        if (eventTypes.indexOf($this.attr('data-type')) === -1) {
          $this.attr('data-display', false);
        } else {
          $this.attr('data-display', true);
        }
      });

      if (this.options.persistSettings) {
        this.localStorageService.addSetting('currentViewRoles', eventTypes);
      }
    },
    _dragEventHandlers: function ($el) {
      /* Create Events */
      var self = this,
          startPos = 0,
          endPos = 0,
          isDragging = false,
          $calendar = self.$calendar;

      function attachEventHandlers () {
        $('body').off('mouseup.inc-selecting').on('mouseup.inc-selecting', function(e){
          if (!$(e.target).parents('.inc-calendar .inc-body').length && !$(e.target).parents('.modal').length) {
            self.removeModal();
            $calendar.attr('data-selecting', false);
            isDragging = false;
            $el.removeClass('selecting');
          }
        });
        $calendar
        .on('mousedown', '.inc-node', handleMouseDown)
        .on('mouseup', '.inc-node', handleMouseUp)
        .on('mousemove', '.inc-node', handleMouseMove);
      }

      function handleMouseDown (e) {
        if (isRightClick(e)){
          return false;
        } else {
          self.removeModal();
          startPos = $el.index($(this));
          isDragging = true;
          $calendar.attr('data-selecting', true);

          if (typeof e.preventDefault != 'undefined'){ e.preventDefault(); }
        }
      }

      function handleMouseUp (e) {
        var $this = $(this),
            $parentRow = $this.parents('.inc-row'),
            options = {
              top: ( ($parentRow.position().top + $this.outerHeight() + 320) > $(window).height() - $calendar.offset().top) && ($parentRow.position().top - 310 > $calendar.offset().top) ? $parentRow.position().top - 310 : ($parentRow.position().top + $this.outerHeight() - 10),
              // place modal on right of click event if there's room, otherwise place on left of click event.
              left: (e.clientX + self.options.modalWidth) >= $(document).width() ? e.clientX - $parentRow.offset().left - self.options.modalWidth : e.clientX - $parentRow.offset().left,
              title: 'Add a new event'
            }

        if (isRightClick(e)){
          return false;
        } else {
          endPos = $el.index($this);
          if (isDragging){
            selectRange();
            self.createEventModal(options);
          }
          $calendar.attr('data-selecting', false);
          isDragging = false;
        }
      }

      function handleMouseMove (e) {
        if (isDragging){
          endPos = $el.index($(this));
          selectRange();
        }
      }

      function selectRange () {
        $el.removeClass('selecting');
        if (endPos + 1 <= startPos){ // reverse select
          $el.slice(endPos, startPos + 1).addClass('selecting');
        } else {
          $el.slice(startPos, endPos + 1).addClass('selecting');
        }
      }

      function isRightClick (e) {
        if (e.which){
          return (e.which === 3);
        } else if (e.button){
          return (e.button === 2);
        }
        return false;
      }

      attachEventHandlers();
    },
    _fetchCalendarEvents: function () {
      // #TODO remove conversion from and to seconds because API uses seconds and JS/cal uses MS
      if (!this.options.getEventsUrl) {
        return false;
      }

      var self = this,
          url = self.options.getEventsUrl,
          params = {
           end__ge: self.getCalStartVal() / 1000,
           start__lt: self.getCalEndVal() / 1000
          }

      self.$el.addClass('loading-events');
      $.get(url, params).done(function(data){
        for (var i = 0; i < data.length; i++) {
          var ev = data[i];
          ev.start = ev.start * 1000;
          ev.end = ev.end * 1000;
        }
        self.options.events = data;
        self.addCalendarEvents();
        self.options.onEventGet(data, self.$calendar);
      }).fail(function(data){
        self.options.onFetchFail(data);
      }).always(function(){
        self.$el.removeClass('loading-events');
        self.options.onEventAlways();
      });
    },
    addCalendarEvents: function (eventsArray) {
      var self = this,
          events = eventsArray || self.options.events,
          calView = self.options.currentView,
          viewRoles = self.options.currentViewRoles,
          weekTitle = self.$calendar.find('.inc-week-day'),
          weekTitleCol = weekTitle.length ? weekTitle.outerWidth() : 0,
          msPerMinute = 60 * 1000,
          msPerHour = msPerMinute * 60,
          msPerDay = msPerHour * 24,
          msPerWeek = msPerDay * 7,
          calWidth,
          pxHrRatio,
          evt,
          evtIndex = {
            primary: 0,
            secondary: 0,
            vacation: 0
          },
          prevRowCount = self.rowSlots.length,
          maxRowCount = 1,
          rosterIndex = 0;

      if (!events.length) {
        return;
      }

      if (calView === 'week') {
        calWidth = self.$calendar.width() - weekTitleCol;
        // pixel to hour ratio, each calendar row represents one day
        pxHrRatio = calWidth / 24;
      } else {
        calWidth = self.$calendar.width();
        // pixel to hour ratio, dividing width of calendar by number of hours in week
        pxHrRatio = calWidth / 168;
      }

      // sort event array so events with the same role are lined up together
      events.sort(function(a, b) {
        var diff = self.options.roleOrder[a.role] - self.options.roleOrder[b.role];
        if (diff === 0) {
          diff = a.start - b.start;
        }
        return diff;
      });

      for (var i = 0; i < events.length; i++) {
        evt = events[i];
        evt.origStart = evt.start;
        evt.origEnd = evt.end;
        if (calView === 'template') {
          // skip extra calculations not needed for template view
          formatTemplateEvent(evt);
          if (maxRowCount > self.options.rowCount) {
            self.addCalendarRows(maxRowCount - self.options.rowCount);
            self.options.rowCount = maxRowCount;
          }
          drawEvents(evt);
        } else {
          trimEvent(evt);
          formatEvent(evt);
          if (!evt.outsideScope) {
            drawEvents(evt);
          }
        }
      }

      // expand calendar block height to fit all events
      if (prevRowCount !== self.rowSlots.length) {
        var extraRows;
        if (prevRowCount === 0)  {
          // FIXME: remove use of magic number 3
          extraRows = self.rowSlots.length - prevRowCount - 3;
        } else {
          extraRows = self.rowSlots.length - prevRowCount;
        }
        if (extraRows > 0) {
          var nodes = $('.inc-node');
          var nodeHeight = $(nodes[0]).height() + extraRows * self.options.eventHeight;
          for (var i = 0; i < nodes.length; i ++) {
            $(nodes[i]).height(nodeHeight);
          }
        }
      }

      function formatEvent (evt) {
        // format event obj for display
        if (!evt.formatted) {
          // convert to ms
          evt.startDateObj = self._createMoment(evt.start, 'x');
          evt.endDateObj = self._createMoment(evt.end, 'x');
          evt.origStartDateObj = self._createMoment(evt.origStart, 'x');
          evt.origEndDateObj = self._createMoment(evt.origEnd, 'x');
          evt.DSTOffset = self.getDSTOffset(evt);
          if (evt.DSTOffset) { evt.end += evt.DSTOffset * msPerHour; };
          evt.startDate = evt.startDateObj.format(self.options.dateFormat);
          evt.startHour = evt.startDateObj.hours();
          evt.startMnt = evt.startDateObj.minutes();
          evt.endDate = evt.endDateObj.format(self.options.dateFormat);
          evt.endHour = evt.endDateObj.hours();
          evt.endMnt = evt.endDateObj.minutes();
          evt.$startEl = $('.inc-node[data-date="' + evt.startDate + '"]:first').length ? $('.inc-node[data-date="' + evt.startDate + '"]:first') : $('.inc-node:first');
          evt.$startRow = evt.$startEl.parents('.inc-row');
          evt.index = evtIndex[evt.role]++;
          evt.top = calEventLayoutRow(evt) * self.options.eventHeight;
          evt.width = calcWidth(evt);
          evt.left = calcLeftPos(evt);
          evt.leftover = calcLeftover(evt);
          evt.rows = 1 + Math.ceil(evt.leftover / calWidth);
          evt.showDetailsModal = true;
          evt.formatted = true;
        }
      }

      function formatTemplateEvent (evt) {
        // template event is value based instead of date based. start and end are passed in as seconds from 0 ( sunday 12:00 default )
        if (!evt.formatted) {
          evt.dStart = evt.origStart >= msPerWeek ? evt.start - msPerWeek * Math.floor(evt.origStart / msPerWeek): evt.start;
          evt.dEnd = evt.origStart >= msPerWeek ? evt.end - msPerWeek * Math.floor(evt.origStart / msPerWeek): evt.end;
          evt.$startEl = $('.inc-node:first');
          evt.$startRow = $('.inc-row:eq(' + (1 + Math.floor(evt.origStart / msPerWeek)) + ')');
          evt.startHour = parseInt(evt.dStart / 36e5);
          evt.startMnt = Math.floor(evt.dStart % 36e5 / 1000 / 60);
          evt.top = (calEventLayoutRow(evt) - 1) * self.options.eventHeight + 2;
          evt.width = calcWidth(evt);
          evt.left = calcLeftPos(evt);
          evt.leftover = calcLeftover(evt);
          evt.rows = 1 + Math.ceil(evt.leftover / calWidth);
          evt.formatted = true;
          maxRowCount = evt.rows > maxRowCount ? evt.rows : maxRowCount;
        }
      }

      function trimEvent (evt) {
        var calStart = self.getCalStartVal(),
            calEnd = self.getCalEndVal();

        // trim event to scope of current cal display
        if ( evt.end < calStart || evt.start > calEnd ) {
          evt.outsideScope = true;
          return;
        }

        if ( evt.start < calStart ) {
          evt.start = calStart;
        }

        if ( evt.end > calEnd ) {
          evt.end = calEnd;
        }
      }

      function calcLeftPos (evt) {
        return Math.floor(evt.$startEl.position().left + ((evt.startHour + (evt.startMnt / 60)) * pxHrRatio));
      }

      function calEventLayoutRow (evt) {
        var conflict, row;
        for (var i = 0; i < self.rowSlots.length; i++) {
          conflict = false;
          row = self.rowSlots[i];
          for (var j = 0; j < row.length; j++) {
              var start = row[j].origStart, end = row[j].origEnd;
              if (start >= evt.origEnd || end <= evt.origStart) {
                  continue;
              } else {
                conflict = true;
                break;
              }
          }
          if (conflict === false) {
            row.push(evt);
            return i+1;
          }
        }
        // conflits in all rows, add a new one
        self.rowSlots.push([evt]);
        return self.rowSlots.length;
      }

      function calcWidth (evt) {
        // get event length in hours, return pixel width for event.
        return (evt.end - evt.start) / 36e5 * pxHrRatio;
      }

      function calcLeftover (evt) {
        // calculate leftover width after initial row positioning.
        return Math.max(0, evt.width - (calWidth + weekTitleCol - evt.left));
      }

      function drawEvents (evt) {
        var startPos = calView === 'month' ? 0 : weekTitleCol;

        function createEventElement (left, top, width) {
          var evtHtmlString = evt.displayString || '<span class="inc-event-name">' + ( evt.full_name || evt.user ) + '</span> <span class="inc-event-date"> ' + evt.origStartDateObj.format('M/D/YYYY HH:mm') + ' to ' + evt.origEndDateObj.format('M/D/YYYY HH:mm') + '</span>',
              evtDisplayString = evt.displayString || ( evt.full_name || evt.user ) + ' ' + evt.origStartDateObj.format('M/D/YYYY HH:mm') + ' to ' + evt.origEndDateObj.format('M/D/YYYY HH:mm');

          return $('<div class="inc-event" />')
            .html(evtHtmlString)
            .attr('title', evtDisplayString)
            .attr('data-type', evt.role)
            .attr('data-id', evt.id)
            .attr('data-parent-id', evt.parentId)
            .attr('data-schedule-id', evt.schedule_id)
            .attr('data-link-id', evt.link_id)
            .attr('data-display', viewRoles.indexOf(evt.role) !== -1 || self.options.persistSettings === false ? 'true' : 'false')
            .css({
              width: Math.ceil(width),
              left: Math.ceil(left),
              top: evt.top
            })
            .on('mouseover', function () {
              self.options.onEventMouseover($(this), evt);
            })
            .on('mouseout', function () {
              self.options.onEventMouseout($(this), evt);
            })
            .on('click', function (e) {
              e.stopPropagation();
              if (evt.showDetailsModal) {
                self.removeModal();
                self.eventDetailsModal(e, evt);
              }
              self.options.onEventClick(evt, e);
            });
        }

        // create first row
        var firstRowWidth = evt.width - evt.leftover;
        createEventElement(evt.left, 0, firstRowWidth).appendTo(evt.$startRow);
        // create the remaining rows
        var leftover = evt.leftover;
        while (leftover > 0) {
          createEventElement(startPos, 0, Math.min(leftover, calWidth))
            .appendTo(evt.$startRow = evt.$startRow.next());
          leftover -= calWidth;
        }
        evt.$startRow = evt.$startEl.parents('.inc-row'); // reset start row after plotting for future plotting
      }

      // after events are drawn

      self.updateEventTypes();
      self.options.onAddEvents(events);
    },
    updateEventTypes: function () {
      var opts = this.options,
          events = opts.events,
          types = opts.eventTypes = [];

      for (var i = 0; i < events.length; i++) {
        if (types.indexOf(events[i].role) === -1) {
          types.push(events[i].role);
        }
      }
    },
    removeEventFromRowSlots: function(ev) {
      for (var i = 0; i < this.rowSlots.length; i++) {
        var row = this.rowSlots[i];
        for (var j = 0; j < row.length; j++) {
          if (row[j].id == ev.id) {
            row.splice(j, 1);
            return;
          }
        }
      }
    },
    clearCalendarEvents: function () {
      this.options.eventTypes = []; // reset event type array before rendering new events.
      this.$calendar.find('.inc-event').remove();
    },
    refreshCalendarEvents: function (eventsArray, isFullRedraw) {
      // Restores calendar events to be in sync with the self.options.events model or event passed in.
      this.clearCalendarEvents();
      if (isFullRedraw === true) {
        for (var i = 0; i < eventsArray.length; i++) {
            eventsArray[i].formatted = false;
        }
        this.rowSlots = [];
      }
      this.addCalendarEvents(eventsArray);
    },
    refetchCalendarEvents: function () {
      // Clears calendar, fetches and draws events again
      this.clearCalendarEvents();
      this._fetchCalendarEvents()
    },
    _renderOverrideOptions: function ($modal, start, end, role) {
      var start = start || this._createMoment($modal.find('#inc-event-start-date').val() + ' ' + $modal.find('#inc-event-start-time').val()).valueOf(),
          end = end || this._createMoment($modal.find('#inc-event-end-date').val() + ' ' + $modal.find('#inc-event-end-time').val()).valueOf(),
          role = role || $modal.find('#inc-role').val(),
          user = $modal.find('#inc-event-user').val(),
          eventItems = '',
          events = this.getEventsWithinRange(start, end, role);

      if (events.length) {
        for (var i = 0, item; i < events.length; i++) {
          item = events[i];
          if (item.user !== user) {
            eventItems += '<li title="' + item.role + '" data-type="' + item.role + '"><input type="checkbox" data-id=' + item.id + ' id="event-' + item.id + '"><label for="event-' + item.id + '">' + item.user + '<br />' + this._createMoment(item.start, 'x').format('M/D/YYYY HH:mm') + ' to ' + this._createMoment(item.end, 'x').format('M/D/YYYY HH:mm') + '</label></li>';
          }
        }
      }
      $modal.find('#inc-override-event-list').html(eventItems.length ? eventItems : 'No events found matching criteria.').find('input[type="checkbox"]:first').prop('checked', true);
    },
    _fetchSwapOptions: function () {
      var self = this,
          url = self.options.getEventsUrl,
          params = {
           start__ge: self.options.today.valueOf() / 1000
          }

      return $.get(url, params);
    },
    _renderSwapOptions: function ($modal, user, role, toLinked) {
      var self = this,
          $fromEvent = $modal.find('.inc-swap-from-event'),
          fromUser = $fromEvent.attr('data-user'),
          fromId = parseInt($fromEvent.attr('data-id')),
          fromEvent = self.options.events.filter(function(i){ return i.id === fromId })[0],
          role = role || fromEvent.role,
          fromLinkId = fromEvent.link_id,
          fromLinkedEvents,
          fromLinked = $modal.find('#toggle-swap-linked-from').prop('checked'),
          toLinked = $modal.find('#toggle-swap-linked-to').prop('checked'),
          $ul = $modal.find('#inc-event-details-swap'),
          users = [];

      // render swap from events

      if (fromLinked && fromLinkId) {
        fromLinkedEvents = self.options.events.filter(function(i){ return i.link_id === fromLinkId });

        $fromEvent
          .html(fromEvent.origStartDateObj.format('M/D/YYYY HH:mm') + ' ( ' + fromLinkedEvents.length + ' events ) ')
          .attr('data-linked', true);
      } else {
        $fromEvent
          .html(fromEvent.origStartDateObj.format('M/D/YYYY HH:mm') + ' to ' + fromEvent.origEndDateObj.format('M/D/YYYY HH:mm'))
          .attr('data-linked', false);
      }

      // build swap-to events

      // Get event swap options from API
      self._fetchSwapOptions().done(function(data){
        self.options.swapEvents = data.sort(function(a, b){ return a.start > b.start ? 1 : -1 });

        $ul.html(
          $('<li />')
          .append('<label class="label-col">User: </label>')
          .append(
            $('<select class="input-col" id="inc-swap-user" name="inc-swap-user" />')
            .append(function(){
              var options = '';

              for (var i = 0, item; i < data.length; i++) {
                item = self.options.swapEvents[i];
                if (item.user !== fromUser && users.indexOf(item.user) === -1) {
                  if (!user) { user = item.user } // Set default user to first non-fromUser user.
                  users.push(item.user);
                  options += '<option value="' + item.user +'" ' + (item.user === user ? 'selected': '') + '>' + item.user +'</option>';
                }
              }

              return options;
            })
            .on('change', function(){
              var user = $(this).val(),
                  role = $modal.find('#inc-swap-role').val();

              self._renderSwapOptions($modal, user, role, toLinked);
            })
          )
        )
        .append(
          $('<li />')
          .append('<label class="label-col">Role: </label>')
          .append(
            $('<select class="input-col" id="inc-swap-role" name="inc-swap-role" />')
            .append(function(){
              var options = '';
              for (var i = 0, item; i < self.options.roles.length; i++) {
                item = self.options.roles[i].name;
                options += '<option value="' + item + '" '  + (item === role ? 'selected': '') + '>' + item + '</option>';
              }

              return options;
            })
            .on('change', function(){
              var role = $(this).val(),
                  user = $modal.find('#inc-swap-user').val();

              self._renderSwapOptions($modal, user, role, toLinked);
            })
          )
        )
        .append(
          $('<li class="toggle-input" />')
          .append(
            $('<label class="label-col label-swap-linked-to">Swap with linked events</label>')
          )
          .append(
            $('<input type="checkbox" id="toggle-swap-linked-to" ' + (toLinked ? 'checked' : '') + '>')
            .on('click', function(){
              var $this = $(this);

              self._renderSwapOptions($modal, user, role, toLinked);
            })
          )
          .append('<label for="toggle-swap-linked-to"></label>')
        )
        .append(
          $('<li />')
          .append('<label class="label-col">Event: </label>')
          .append(
            $('<ul id="inc-swap-event-list" />')
            .html(function(){
              var eventItems = '',
                  toLinkedEventsMap = {};

              if (toLinked) {
                // render sets of linked events.

                for (var i = 0, item; i < self.options.swapEvents.length; i++) {
                  item = self.options.swapEvents[i];

                  if(item.link_id) {
                    if (item.link_id in toLinkedEventsMap) {
                      toLinkedEventsMap[item.link_id].push(item);
                    } else {
                      toLinkedEventsMap[item.link_id] = [item];
                    }
                  }
                }

                for (var i = 0, keys = Object.keys(toLinkedEventsMap), item, linkedItem; i < keys.length; i++) {
                  linkedItem = toLinkedEventsMap[keys[i]];
                  item = linkedItem[0];
                  if (item.user === user && item.role === role) {
                    eventItems += '<li title="' + item.role + '" data-type="' + item.role + '"><input type="radio" ' + (eventItems === '' ? 'checked = true' : '') + ' name="inc-swap-event" value="' + item.id + '" data-id=' + item.id + ' data-link-id="' + item.link_id + '" data-schedule-id="' + item.schedule_id + '" data-linked="true" id="event-' + item.id + '"><label for="event-' + item.id + '">' + self._createMoment(item.start, 'X').format('M/D/YYYY HH:mm') + ' ( ' + linkedItem.length + ' events )</label></li>';
                  }
                }

              } else {
                // render singular events.
                for (var i = 0, item; i < self.options.swapEvents.length; i++) {
                  item = self.options.swapEvents[i];
                  if (item.user === user && item.role === role) {
                    eventItems += '<li title="' + item.role + '" data-type="' + item.role + '"><input type="radio" ' + (eventItems === '' ? 'checked = true' : '') + ' name="inc-swap-event" value="' + item.id + '" data-id=' + item.id + ' data-link-id="' + item.link_id + '" data-schedule-id="' + item.schedule_id + '" id="event-' + item.id + '"><label for="event-' + item.id + '">' + self._createMoment(item.start, 'X').format('M/D/YYYY HH:mm') + ' to ' + self._createMoment(item.end, 'X').format('M/D/YYYY HH:mm') + '</label></li>';
                  }
                }
              }

              return eventItems ? eventItems : 'No events found matching criteria. (Note: You can not swap with events starting on or before today)';
            })
          )
        )
      });
    },
    createEventModal: function (options) {
      if (!options || typeof(options) !== 'object') {
        return 'Options required for creating modal';
      }

      var title = options.title || 'Add a new event',
          self = this,
          $calendar = self.$calendar,
          $calBody = $calendar.find('.inc-body'),
          $modal = $('<div class="inc-modal inc-create-event-modal" data-12-hour="false"/>'),
          startDate = $calendar.find('.selecting:first').attr('data-date'),
          endDate = $calendar.find('.selecting:last').attr('data-date'),
          startTime = $calendar.find('.selecting:first').attr('data-time'),
          endTime = self.options.currentView === 'week' ? parseInt(($calendar.find('.selecting:last').attr('data-time')).split(':')[0]) + 1 + ':00' : '24:00'; // for week view, add 1 to the end time. probably should have a better implementation

      $modal
      .on('click', function(e){
        e.stopPropagation();
      })
      .css(
        {
          width: self.options.modalWidth,
          top: options.top,
          left: options.left
        }
      )
      .append(
        $('<h4 />')
        .text(title)
        .append(
          $('<span class="inc-modal-top-actions" />')
          .append(
            $('<span class="inc-modal-close" />')
            .html('<i class="inc-icon inc-icon-close"><svg xmlns="http://www.w3.org/2000/svg" width="10px" height="10px" viewBox="0 0 8 8"><path d="M1.41 0l-1.41 1.41.72.72 1.78 1.81-1.78 1.78-.72.69 1.41 1.44.72-.72 1.81-1.81 1.78 1.81.69.72 1.44-1.44-.72-.69-1.81-1.78 1.81-1.81.72-.72-1.44-1.41-.69.72-1.78 1.78-1.81-1.78-.72-.72z" /></svg></i>')
            .click(function(){
              self.removeModal();
            })
          )
        )
      )
      .append(
        $('<ul class="inc-event-details" />')
        .append(
          $('<li />')
          .append(
            $('<li />')
            .append(
              $('<li />')
              .append('<label class="label-col">User: </label>')
              .append(
                $('<div class="input-col" />')
                .append('<input type="text" class="typeahead" data-type="team_users" id="inc-event-user" name="inc-event-user" placeholder="username" value="' + self.options.user + '" style="width:100px" /> ')
              )
            )
            .append('<label class="label-col">Start: </label>')
            .append(
              $('<input type="text" class="' + this.options.datePickerClass + '" id="inc-event-start-date" name="inc-event-start-date" placeholder="YYYY/MM/DD" value="' + startDate + '" style="width:100px" /> ')
              .on('change', function(){
                self._renderOverrideOptions($modal);
              })
            )
            .append(
              $('<input type="text" id="inc-event-start-time" name="inc-event-start-time" placeholder="HH:MM" value="' + startTime + '" style="width:60px" />')
              .on('change', function(){
                self._renderOverrideOptions($modal);
              })
            )
            .append('<label class="small"> TZ: ' + (self.options.timezone ? self.options.timezone : 'System time') + '</label>')
          )
          .append(
            $('<li />')
            .append('<label class="label-col">End: </label>')
            .append(
              $('<input type="text" class="' + this.options.datePickerClass + '" id="inc-event-end-date" name="inc-event-end-date" placeholder="YYYY/MM/DD" value="' + endDate + '" style="width:100px" /> ')
              .on('change', function(){
                self._renderOverrideOptions($modal);
              })
            )
            .append(
              $('<input type="text" id="inc-event-end-time" name="inc-event-end-time" placeholder="HH:MM" value="' + endTime + '" style="width:60px" />')
              .on('change', function(){
                self._renderOverrideOptions($modal);
              })
            )
            .append('<label class="small"> TZ: ' + (self.options.timezone ? self.options.timezone : 'System time') + '</label>')
          )
          .append(
            $('<li />')
            .append('<label class="label-col">Role: </label>')
            .append(
              $('<select class="input-col" id="inc-role" name="inc-role" />')
              .append(function(){
                var options = '';

                for (var i = 0; i < self.options.roles.length; i++) {
                  var roleName = self.options.roles[i].name;
                  options += '<option value="' + roleName + '">' + roleName + '</option>';
                }

                return options;
              })
              .on('change', function(){
                self._renderOverrideOptions($modal);
              })
            )
          )
          .append(
            $('<li />')
            .append('<label class="label-col">Note: </label>')
            .append(
              $('<div class="input-col" />')
              .append('<input type="text" id="inc-event-note" name="inc-event-note" value="" style="width:100%" /> ')
            )
          )
          .append(
            $('<li class="toggle-input" />')
            .append(
              $('<label class="label-col label-override">12 Hour </label>')
            )
            .append(
              $('<input type="checkbox" id="toggle-12-hour-mode">')
              .on('click', function(){
                var $this = $(this),
                    $modal = $this.parents('.inc-create-event-modal');
                    $modal.attr('data-12-hour', $this.prop('checked') ? true : false);
              })
            )
            .append('<label for="toggle-12-hour-mode"></label>')
          )
          .append('<h5 class="divider-text override-content"> Substitute </h5>')
          .append(
            $('<li class="toggle-input override-content" />')
            .append(
              $('<label class="label-col label-override">Substitute <i class="inc-icon inc-icon-question-circle svg-icon-question" title="Learn about event substitution."><svg xmlns="http://www.w3.org/2000/svg" width="10px" height="10px" viewBox="0 0 10 10"><path d="M2.47 0c-.85 0-1.48.26-1.88.66-.4.4-.54.9-.59 1.28l1 .13c.04-.25.12-.5.31-.69.19-.19.49-.38 1.16-.38.66 0 1.02.16 1.22.34.2.18.28.4.28.66 0 .83-.34 1.06-.84 1.5-.5.44-1.16 1.08-1.16 2.25v.25h1v-.25c0-.83.31-1.06.81-1.5.5-.44 1.19-1.08 1.19-2.25 0-.48-.17-1.02-.59-1.41-.43-.39-1.07-.59-1.91-.59zm-.5 7v1h1v-1h-1z" transform="translate(2)" /></svg></i></label>')
              .on('click', function(){
                $('#override-details-modal').modal({top: '50%'});
              })
            )
            .append(
              $('<input type="checkbox" id="toggle-override-mode">')
              .on('click', function(){
                var $this = $(this),
                    $modal = $this.parents('.inc-create-event-modal');

                $modal.attr('data-override', $this.prop('checked') ? true : false);
                self._renderOverrideOptions($modal);
              })
            )
            .append('<label for="toggle-override-mode"></label>')
          )
        )
        .append(
          $('<li class="inc-event-override" />')
          .append('<label>Events to substitute: </label>')
          .append(
            $('<ul id="inc-override-event-list" />')
            .text('No events found matching criteria.')
          )
        )
      )
      .append(
        $('<div class="inc-modal-actions" />')
        .append('<div class="error-text"></div>')
        .append(
          $('<button class="btn btn-primary">Save</button>')
          .on('click', function(){
            var $modal = $(this).parents('.inc-modal'),
                event_ids = [],
                override,
                twelveHour;

            //#TODO: Figure out a way to format event specifically for what the api accepts. currently the API accepts seconds vs ms
            var evt = {
              role: $modal.find('#inc-role').val(),
              start: self._createMoment($modal.find('#inc-event-start-date').val() + ' ' + $modal.find('#inc-event-start-time').val()).valueOf(),
              end: self._createMoment($modal.find('#inc-event-end-date').val() + ' ' + $modal.find('#inc-event-end-time').val()).valueOf(),
              team: self.options.team,
              user: $modal.find('#inc-event-user').val(),
            }

            var note = $modal.find('#inc-event-note').val();
            if (!!note) {
              evt.note = note;
            }

            if ($modal.attr('data-override') === "true") {
              // override logic goes here
              $('#inc-override-event-list').find('input[type="checkbox"]:checked').each(function(){
                event_ids.push(parseInt($(this).attr('data-id')));
              });
              evt.event_ids = event_ids;
              override = true;
              if (event_ids.length === 0) {
                $modal.find('.error-text').text('Please select events to substitute or turn the "substitute" toggle off.');
                return;
              }
            }
            if ($modal.attr('data-12-hour') === "true") {
              // Can't override and create 12 hour event at the same time
              override = false;
              twelveHour = true;
            }
            self.saveEvent($modal, evt, override, twelveHour);
          })
        )
        .append(
          $('<button class="btn btn-blue">Cancel</button>')
          .on('click', function(){
            self.removeModal();
          })
        )
      )
      .appendTo($calBody);
      self.options.onModalOpen($modal, $calendar);
    },
    eventDetailsModal: function (e, evt) {
      var title = evt.user || 'Event Details',
          self = this,
          $calendar = self.$calendar,
          $calBody = $calendar.find('.inc-body'),
          $modal = $('<div class="inc-modal inc-event-details-modal" data-mode="view" data-role="' + evt.role + '" data-event-id="' + evt.id + '" />'),
          $eventItem = $(e.target).hasClass('inc-event') ? $(e.target) : $(e.target).parents('.inc-event'),
          $parentRow = $eventItem.parents('.inc-row');

      $modal
      .on('click', function(e){
        e.stopPropagation();
      })
      .css(
        {
          width: self.options.modalWidth,
          top: ($parentRow.position().top + $eventItem.position().top + $eventItem.height() + 320) > $(window).height() - $calendar.offset().top ? $parentRow.position().top + $eventItem.position().top + $eventItem.height() - 310 : $parentRow.position().top + $eventItem.position().top + $eventItem.height(),
          left: (e.clientX + self.options.modalWidth) >= $(document).width() ? (e.clientX - $parentRow.offset().left) - self.options.modalWidth : e.clientX - $parentRow.offset().left // place modal on right of click event if there's room, otherwise place on left of click event.
        }
      )
      .append(
        $('<h4 />')
        .html('<span class="inc-event-details-title">' + title + '</span>')
        .append(
          $('<span class="inc-modal-top-actions" />')
          .append(
            $('<span class="inc-modal-swap inc-edit-action" title="Swap shift" />')
            .html('<i class="inc-icon inc-icon-swap"><svg viewBox="0 0 24 24" width="20px" height="20px" x="0" y="0" preserveAspectRatio="xMinYMin meet"><g style="fill-opacity: 1"><g transform="translate(-1166.000000, -354.000000)"><path d="M1166.29003,358.71 L1169.59003,362 L1170.88003,360.71 L1169.17003,359 L1180.05859,358.999634 L1180.05859,357.063965 L1169.17003,357 L1170.88003,355.29 L1169.59003,354 L1166.29003,357.29 C1166.10303,357.479 1165.99803,357.734 1166.00003,358 C1165.99803,358.266 1166.10303,358.521 1166.29003,358.71 Z M1179.76857,364.29 L1176.46857,361 L1175.17857,362.29 L1176.88857,364 L1166,364.000366 L1166,365.936035 L1176.88857,366 L1175.17857,367.71 L1176.46857,369 L1179.76857,365.71 C1179.95557,365.521 1180.06057,365.266 1180.05857,365 C1180.06057,364.734 1179.95557,364.479 1179.76857,364.29 Z"></path></g></g></svg></i>')
            .click(function(){
              self._toggleModalSwap($(this));
            })
          )
          .append(
            $('<span class="inc-modal-edit inc-edit-action" title="Edit shift" />')
            .html('<i class="inc-icon inc-icon-pencil"><svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" viewBox="0 0 12 12"><path d="M6 0l-1 1 2 2 1-1-2-2zm-2 2l-4 4v2h2l4-4-2-2z" /></svg></i>')
            .click(function(){
              self._toggleModalEdit($(this));
            })
          )
          .append(
            $('<span class="inc-modal-close" title="Close modal" />')
            .html('<i class="inc-icon inc-icon-close"><svg xmlns="http://www.w3.org/2000/svg" width="10px" height="10px" viewBox="0 0 8 8"><path d="M1.41 0l-1.41 1.41.72.72 1.78 1.81-1.78 1.78-.72.69 1.41 1.44.72-.72 1.81-1.81 1.78 1.81.69.72 1.44-1.44-.72-.69-1.81-1.78 1.81-1.81.72-.72-1.44-1.41-.69.72-1.78 1.78-1.81-1.78-.72-.72z" /></svg></i>')
            .click(function(){
              self.removeModal();
            })
          )
        )
      )
      .append(
        $('<ul class="inc-event-details inc-event-details-view" />')
        .append(
          $('<li />')
          .append('<label class="label-col">Start: </label>')
          .append('<span class="data-col">' + evt.origStartDateObj.format('M/D/YYYY HH:mm') + '</span> <label class="small"> TZ: ' + (self.options.timezone ? self.options.timezone : 'System time') + '</label>')
        )
        .append(
          $('<li />')
          .append('<label class="label-col">End: </label>')
          .append('<span class="data-col">' + evt.origEndDateObj.format('M/D/YYYY HH:mm') + '</span> <label class="small"> TZ: ' + (self.options.timezone ? self.options.timezone : 'System time') + '</label>')
        )
        .append(
          $('<li />')
          .append('<label class="label-col">Role: </label>')
          .append('<span class="data-col">' + evt.role + '</span>')
        )
        .append(
          $('<li />')
          .append('<label class="label-col">User: </label>')
          .append('<span class="data-col">' + evt.user + '</span>')
        )
        .append(function(){
          if (evt.note) {
            return $('<li />')
              .append('<label class="label-col">Note: </label>')
              .append('<span class="data-col">' + (Handlebars.Utils.escapeExpression(evt.note) || "") + '</span>')
          }
        })
      )
      .append(
        $('<div class="inc-event-details inc-event-details-edit" />')
        .append(
          $('<ul />')
          .append(
            $('<li />')
            .append('<label class="label-col">User: </label>')
            .append(
              $('<div class="input-col" />')
              .append(
                $('<input type="text" class="typeahead" id="inc-event-user" name="inc-event-user" placeholder="username" value="' + evt.user + '" style="width:100px" /> ')
              )
            )
          )
          .append(
            $('<li data-linked-editable="false" />')
            .append('<label class="label-col">Start: </label>')
            .append(
              $('<input type="text" class="' + this.options.datePickerClass + '" id="inc-event-start-date" name="inc-event-start-date" placeholder="YYYY/MM/DD" value="' + evt.origStartDateObj.format('YYYY/M/D') + '" style="width:100px" /> ')
            )
            .append(
              $('<input type="text" id="inc-event-start-time" name="inc-event-start-time" placeholder="HH:MM" maxlength="5" value="' + evt.origStartDateObj.format('HH:mm') + '" style="width:60px" />')
            )
            .append('<label class="small"> TZ: ' + (self.options.timezone ? self.options.timezone : 'System time') + '</label>')
          )
          .append(
            $('<li data-linked-editable="false" />')
            .append('<label class="label-col">End: </label>')
            .append(
              $('<input type="text" class="' + this.options.datePickerClass + '" id="inc-event-end-date" name="inc-event-end-date" placeholder="YYYY/MM/DD" value="' + evt.origEndDateObj.format('YYYY/M/D') + '" style="width:100px" /> ')
            )
            .append(
              $('<input type="text" id="inc-event-end-time" name="inc-event-end-time" placeholder="HH:MM" maxlength="5" value="' + evt.origEndDateObj.format('HH:mm') + '" style="width:60px" />')
            )
            .append('<label class="small"> TZ: ' + (self.options.timezone ? self.options.timezone : 'System time') + '</label>')
          )
          .append(
            $('<li />')
            .append('<label class="label-col">Role: </label>')
            .append(
              $('<select class="input-col" id="inc-role" namei="inc-role" />')
              .append(function(){
                var options = '';

                for (var i = 0, item; i < self.options.roles.length; i++) {
                  item = self.options.roles[i].name;
                  options += '<option value="' + item + '"' + (evt.role === item ? 'selected' : '') + '>' + item + '</option>';
                }

                return options;
              })
            )
          )
          .append(
            $('<li />')
            .append('<label class="label-col">Note: </label>')
            .append(
              $('<div class="input-col" />')
              .append('<input type="text" id="inc-event-note" name="inc-event-note" value="' + (Handlebars.Utils.escapeExpression(evt.note) || '') + '" style="width:100%" /> ')
            )
          )
          .append(function(){
            if (evt.link_id) {
              return $('<li class="toggle-input" />')
                .append(
                  $('<label class="label-col label-swap-linked-to">Modify all linked events</label>')
                )
                .append(
                  $('<input type="checkbox" id="toggle-edit-linked">')
                  .on('click', function(){
                    var $this = $(this),
                        $modal = $this.parents('.inc-event-details-modal'),
                        $editEventTab = $this.parents('.inc-event-details-edit');

                    if ($(this).prop('checked')) {
                      $editEventTab.attr('data-edit-linked', true);
                      $calendar.find('.inc-event[data-link-id="' + evt.link_id + '"]').attr('data-force-highlighted', true);
                    } else {
                      $editEventTab.attr('data-edit-linked', false);
                      $calendar.find('.inc-event[data-link-id="' + evt.link_id + '"]').attr('data-force-highlighted', false);
                      $eventItem.attr('data-force-highlighted', true);
                    }
                  })
                )
                .append('<label for="toggle-edit-linked"></label>')
            }
          })
        )
        .append(
          $('<div class="inc-modal-actions" />')
          .append('<div class="error-text"></div>')
          .append(
            $('<button class="btn btn-danger pull-left">Delete</button>')
            .on('click', function(){
              self.deleteEvent($modal, evt);
            })
          )
          .append(
            $('<button class="btn btn-primary">Save</button>')
            .on('click', function(){
              var $modal = $(this).parents('.inc-modal'),
                  updatedEvt = {}

              //#TODO: Figure out a way to format event specifically for what the api accepts. currently the API accepts seconds
              updatedEvt.id = evt.id;
              updatedEvt.link_id = evt.link_id;
              updatedEvt.role = $modal.find('#inc-role').val();
              updatedEvt.start = self._createMoment($modal.find('#inc-event-start-date').val() + ' ' + $modal.find('#inc-event-start-time').val()).valueOf();
              updatedEvt.end = self._createMoment($modal.find('#inc-event-end-date').val() + ' ' + $('#inc-event-end-time').val()).valueOf();
              updatedEvt.user = $('#inc-event-user').val();
              updatedEvt.note = $('#inc-event-note').val();
              self.updateEvent($modal, updatedEvt);
            })
          )
          .append(
            $('<button class="btn btn-blue">Cancel</button>')
            .on('click', function(){
              self.removeModal();
            })
          )
        )
      )
      .append(
        $('<div class="inc-event-details inc-event-details-swap" />')
        .append(
          $('<ul />')
          .append('<h5 class="divider-text"> From </h5>')
          .append(
            $('<li />')
            .append('<label class="label-col">User: </label>')
            .append('<span class="data-col">' + evt.user + '</span>')
          )
          .append(
            $('<li class="toggle-input ' + (evt.link_id ? '' : 'hidden') + '" />')
            .append(
              $('<label class="label-col label-swap-linked">Swap linked events</label>')
            )
            .append(
              $('<input type="checkbox" id="toggle-swap-linked-from">')
              .on('click', function(){
                var $this = $(this),
                    $modal = $this.parents('.inc-event-details-modal');

                if ($(this).prop('checked')) {
                  $calendar.find('.inc-event[data-link-id="' + evt.link_id + '"]').attr('data-force-highlighted', true);
                } else {
                  $calendar.find('.inc-event[data-link-id="' + evt.link_id + '"]').attr('data-force-highlighted', false);
                  $eventItem.attr('data-force-highlighted', true);
                }

                self._renderSwapOptions($modal);
              })
            )
            .append('<label for="toggle-swap-linked-from"></label>')
          )
          .append(
            $('<li />')
            .append('<label class="label-col">Event: </label>')
            .append('<span title="' + evt.role + '" class="data-col inc-swap-from-event" data-type="' + evt.role + '" data-user="' + evt.user + '" data-id="' + evt.id + '" data-link-id="' + evt.link_id + '" data-schedule-id="' + evt.schedule_id + '">' + evt.origStartDateObj.format('M/D/YYYY HH:mm') + ' to ' + evt.origEndDateObj.format('M/D/YYYY HH:mm') + '</span>')
          )
          .append('<h5 class="divider-text"> To </h5>')
          .append(
            $('<ul id="inc-event-details-swap" />')
          )
        )
        .append(
          $('<div class="inc-modal-actions" />')
          .append('<div class="error-text"></div>')
          .append(
            $('<button class="btn btn-primary">Save </button>')
            .on('click', function(){
              var $modal = $(this).parents('.inc-modal');

              self.swapEvents($modal);
            })
          )
          .append(
            $('<button class="btn btn-blue">Cancel</button>')
            .on('click', function(){
              self.removeModal();
            })
          )
        )
      )
      .appendTo($calBody);

      $calendar.find('.inc-event[data-id="' + evt.id + '"]').attr('data-highlighted', true);
      self.options.onModalOpen($modal, $calendar, $eventItem, evt);
      self.options.onEventDetailsModalOpen($modal, $calendar, $eventItem, evt);
    },
    removeModal: function ($el) {
      var $calendar = this.$calendar,
          $modal = $el || $calendar.find('.inc-modal');

      this.$calendar.find('.selecting').removeClass('selecting');
      this.$calendar.find('[data-highlighted="true"]').attr('data-highlighted', false);
      this.$calendar.find('[data-force-highlighted="true"]').attr('data-force-highlighted', false);
      this.options.onModalClose($modal, $calendar);
      this.options.onEventDetailsModalClose($modal, $calendar);
      $modal.remove();
    },
    saveEvent: function ($modal, evt, override, twelveHour) {
      var self = this,
          url = override ? this.options.eventsUrl + '/override' : this.options.eventsUrl;

      if (twelveHour) {
        var start = self._createMoment(evt.start, 'x'),
            cmp = moment(start),
            evts = [];

        url = this.options.eventsUrl + '/link';
        // Make 12 hour events as long as the whole event fits in the given time frame
        // HACK: To add "12 hours," add 1 day, then subtract 12 hours. Needed for DST.
        // Can't just add 12 hours because moment assumes you want exact precision unless
        // you add increments of days or larger. See https://momentjs.com/docs/#/manipulating/add/
        while (cmp.add(1, 'd').subtract(12, 'h').isBefore(evt.end)) {
          // Create a 12 hour long event, then move start forward one day
          evts.push({
            start: start.unix(),
            end: start.add(1, 'd').subtract(12, 'h').unix(),
            team: evt.team,
            role: evt.role,
            user: evt.user,
            note: evt.note
          });
          // Go one day forward and make a new event
          start.add(12, 'h');
          cmp = moment(start);
        }
      }
      // #TODO: convert times to second for API. find a better solution for interacting with api.
      evt.start = evt.start / 1000;
      evt.end = evt.end / 1000;

      var postData = twelveHour ? evts : evt;
      $.ajax({
        type: 'POST',
        url: url,
        dataType: 'html',
        contentType: 'application/json',
        data: JSON.stringify(postData)
      }).done(function(data) {
        evt.start = evt.start * 1000;
        evt.end = evt.end * 1000;
        if (override) {
          self.options.events = self.options.events.filter(function(i){
            // remove self.options.events with the parent ID matching schedule ID
            return evt.event_ids.indexOf(i.id) === -1;
          });
          var modifiedEvents = JSON.parse(data).map(function(i){
            i.start = i.start * 1000;
            i.end = i.end * 1000;
            return i;
          });
          self.options.events = self.options.events.concat(modifiedEvents);
          // @TODO: instead of doing a full refresh, only update changed events
          // and rowSlots
          self.refreshCalendarEvents(self.options.events, true);
        } else if (twelveHour) {
          var response = JSON.parse(data)
          evts = evts.map(function(e, idx){
            e.link_id = response['link_id'];
            e.id = response['event_ids'][idx];
            e.start = e.start * 1000;
            e.end = e.end * 1000;
            return e;
          });
          self.options.events = self.options.events.concat(evts);
          self.addCalendarEvents(evts);
        } else {
          evt.id = parseInt(data);
          self.options.events.push(evt);
          self.addCalendarEvents([evt]);
        }
        self.removeModal();
      }).fail(function(data){
        var error = data.responseText ? JSON.parse(data.responseText).description : "Request Failed";
        $modal.find('.error-text').text(error);
      });
    },
    updateEvent: function ($modal, evt) {
      var self = this,
          events = self.options.events,
          linked = $modal.find('.inc-event-details-edit').data('edit-linked'),
          url = this.options.eventsUrl + '/' + ( linked ? 'link/' + evt.link_id : evt.id );
          submitModel = {
            role: evt.role,
            user: evt.user,
            note: evt.note
          }
      // Can't modify start/end for linked events
      if (!linked) {
        submitModel['start'] = evt.start / 1000;
        submitModel['end'] = evt.end / 1000;
      }
      // #TODO: convert times to second for API. find a better solution for interacting with api.
      $.ajax({
        type: 'PUT',
        url: url,
        dataType: 'html',
        contentType: 'application/json',
        data: JSON.stringify(submitModel)
      }).done(function(data){
        self.options.events.map(function(item){
          var match = linked ? item.link_id === evt.link_id : item.id === evt.id;

          if (match) {
            if (!linked) {
              item.start = evt.start;
              item.end = evt.end;
              item.link_id = null; // break link on individual event swap
            }
            self.removeEventFromRowSlots(item);
            item.role = evt.role;
            item.user = evt.user;
            item.note = evt.note;
            item.formatted = false;
            delete item.full_name;
          }
        });
        self.refreshCalendarEvents();
        self.removeModal();
      }).fail(function(data){
        var error = data.responseText ? JSON.parse(data.responseText).description : 'Request Failed';
        $modal.find('.error-text').text(error);
      });
    },
    swapEvents: function ($modal) {
      var self = this,
          events = self.options.events,
          url = this.options.eventsUrl + '/swap',
          $fromEvent = $modal.find('.inc-swap-from-event'),
          fromId = parseInt($fromEvent.attr('data-id')),
          fromLinkId = $fromEvent.attr('data-link-id'),
          fromLinked = $modal.find('#toggle-swap-linked-from').prop('checked'),
          $toEvent = $modal.find('#inc-swap-event-list').find('input[type="radio"]:checked'),
          toId = parseInt($toEvent.attr('data-id')),
          toLinkId = $toEvent.attr('data-link-id'),
          toLinked = $modal.find('#toggle-swap-linked-to').prop('checked'),
          fromEvent = events.filter(function(i){ return fromLinked ? i.link_id  === fromLinkId : i.id === fromId })[0],
          toEvent = self.options.swapEvents.filter(function(i){ return toLinked ? i.link_id  === toLinkId : i.id == toId })[0],
          submitModel = {
            events: [{id: fromLinked ? fromLinkId : fromId, linked: fromLinked === true ? true : false}, {id: toLinked ? toLinkId : toId, linked: toLinked === true ? true : false }]
          };

      $.ajax({
        type: 'POST',
        url: url,
        dataType: 'html',
        contentType: 'application/json',
        data: JSON.stringify(submitModel)
      }).done(function(data){
        var tmpUser = fromEvent.user,
            tmpFullName = fromEvent.full_name;

        events.map(function(i){
          if (fromLinked && i.link_id === fromLinkId) {
            i.user = toEvent.user;
            i.full_name = toEvent.full_name;
          } else if (i.id === fromEvent.id) {
            i.user = toEvent.user;
            i.full_name = toEvent.full_name;
            i.link_id = null; // break link on individual event swap
          } else if (toLinked && i.link_id === toLinkId) {
            i.user = tmpUser;
            i.full_name = tmpFullName;
          } else if (i.id === toEvent.id) {
            i.user = tmpUser;
            i.full_name = tmpFullName;
            i.link_id = null; // break link on individual event swap
          }
          return i;
        });

        self.refreshCalendarEvents();
        self.removeModal();
      }).fail(function (data) {
        var error = data.responseText ? JSON.parse(data.responseText).description : 'Request Failed';
        $modal.find('.error-text').text(error);
      });
    },
    _toggleModalEdit: function ($el) {
      var $modal = $el.parents('.inc-event-details-modal');
      $modal.attr('data-mode', $modal.attr('data-mode') === 'edit' ? 'view' : 'edit');
    },
    _toggleModalSwap: function ($el) {
      var $modal = $el.parents('.inc-event-details-modal');
      $modal.attr('data-mode', $modal.attr('data-mode') === 'swap' ? 'view' : 'swap');
      this._renderSwapOptions($modal);
    },
    deleteEvent: function ($modal, evt) {
      var self = this,
          events = self.options.events,
          linked = $modal.find('.inc-event-details-edit').data('edit-linked'),
          url = this.options.eventsUrl + '/' + ( linked ? 'link/' + evt.link_id : evt.id );

      $.ajax({
        type: 'DELETE',
        url: url,
        dataType: 'html',
        contentType: 'application/json'
      }).done(function(data){
        self.removeEventFromRowSlots(evt);
        self.options.events = self.options.events.filter(function(i){
          // remove self.options.events with the parent ID matching schedule ID
          if (linked) {
            return i.link_id !== evt.link_id;
          } else {
            return i.id !== evt.id;
          }
        });
        self.refreshCalendarEvents();
        self.removeModal();
      }).fail(function(data){
        var error = data.responseText ? JSON.parse(data.responseText).description : "Request Failed";
        $modal.find('.error-text').text(error);
      });
    }
  }

  InCalendar.prototype.localStorageService = {
    name: 'inc-view-settings',
    settings: null,
    init: function () {
      if (!this.testLocalStorage()) {
        console.debug('Browser does not support local storage');
        return;
      }
      this.settings = JSON.parse(localStorage.getItem(this.name)) || {};
    },
    addSetting: function (setting, val) {
      if (setting && val) {
        this.settings[setting] = val;
      }
      this.saveSettings();
    },
    removeSetting: function (setting) {
      if (setting) {
        delete this.settings[setting];
      }
      this.saveSettings();
    },
    saveSettings: function () {
      localStorage.setItem(this.name, JSON.stringify(this.settings));
    },
    clearSettings: function () {
      localStorage.removeItem(this.name);
    },
    testLocalStorage: function () {
      try {
        localStorage.setItem('inc-test', 'inc-test');
        localStorage.removeItem('inc-test');
        return true;
      } catch (e) {
        return false;
      }
    }
  }

  InCalendar.prototype.datePicker = function() {
    var $datePicker,
        $activeEl,
        cal = this,
        currentDate,
        originalDate,
        datePickerNodeClass = 'inc-date-picker-node',
        datePickerWidgetName = 'inc-date-picker-widget',
        today = moment();

    function init () {
      events();
    }

    function events () {
      cal.$calendar.on('focus', '.' + cal.options.datePickerClass, activateDatePicker);
    }

    function activateDatePicker (e) {
      $activeEl = $(this);
      currentDate = moment($activeEl.val(), $activeEl.attr('placeholder'));
      originalDate = moment($activeEl.val(), $activeEl.attr('placeholder'));
      render(currentDate);
    }

    function buildDatePickerToolbar (date) {
      var $calTitle = $('<div class="inc-toolbar-title" />'),
          $element = $('<div class="inc-toolbar" />'),
          date = date || cal.options.startDate,
          months = cal.options.months,
          monthsShort = cal.options.monthsShort,
          monthTitle = months[date.month()] + ' ' + date.year(),
          view = 'month';

      $element
        .append( $calTitle
          .append( $('<span class="inc-controls-title" />')
            .text( monthTitle )
          )
          .prepend( $('<span class="inc-controls-prev" data-type=' + view + ' />')
            .html('<i class="inc-icon icon-chevron icon-chevron-left"><svg xmlns="http://www.w3.org/2000/svg" width="16px" height="16px" viewBox="0 0 10 8" style="fill: currentColor; opacity: .7;"><path d="M4 0l-4 4 4 4 1.5-1.5-2.5-2.5 2.5-2.5-1.5-1.5z" transform="translate(1)" /></svg></i>')
            .click(function () {
              stepDatePicker('backward');
            })
          )
          .append( $('<span class="inc-controls-next" data-type=' + view + ' />')
            .html('<i class="inc-icon icon-chevron icon-chevron-right"><svg xmlns="http://www.w3.org/2000/svg" width="16px" height="16px" viewBox="0 0 10 8" style="fill: currentColor; opacity: .7;"><path d="M1.5 0l-1.5 1.5 2.5 2.5-2.5 2.5 1.5 1.5 4-4-4-4z" transform="translate(1)" /></svg></i>')
            .click(function () {
              stepDatePicker('forward');
            })
          )
        );

      return $element;
    }

    function buildDatePickerActionBar () {
      var $element = $('<div class="inc-modal-actions" />');

      $element
        .append(
          $('<button class="btn btn-blue">Cancel</button>')
          .on('click', function(){
            removeDatePicker();
          })
        )

      return $element;
    }

    function render (date) {
      var date = date && date._isAMomentObject ? date : moment();

      if ($datePicker) { removeDatePicker() };

      $datePicker = $('<div class="' + datePickerWidgetName + '" id="' + datePickerWidgetName + '" />');
      $activeEl.after($datePicker);

      $datePicker
        .append(buildDatePickerToolbar(date))
        .append(cal._buildCalendar(date, 'month', null, true, datePickerNodeClass))
        .css({
          top: $activeEl.position().top + $activeEl.outerHeight() + 3,
          left: $activeEl.position().left
        })
        .on('click', '.' + datePickerNodeClass, setDate)
        .append(buildDatePickerActionBar());

      // Add active state to selected date.
      $datePicker.find('.' + datePickerNodeClass + '[data-date="' + originalDate.format('YYYY/M/D') + '"]').addClass('selected');
    }

    function stepDatePicker (direction) {
      var dir = direction || 'forward',
          method = dir === 'forward' ? 'add' : 'subtract';

      currentDate[method](1, 'month');
      render(currentDate);
    }

    function setDate () {
      var $this = $(this);

      $activeEl.val($this.data('date'));
      removeDatePicker();
    }

    function removeDatePicker () {
      $datePicker.remove();
    }

    init();
  }

  $.fn.incalendar = function (options) {
    var args = Array.prototype.slice.call(arguments, 1);

    if (options === undefined || typeof options === 'object') {
      return this.each(function () {
        if (!$.data(this, pluginName)) {
          $.data(this, pluginName, new InCalendar(this, options));
        }
      });
    } else if (typeof options === 'string' && options[0] !== '_' && options !== 'init') {
      var call;
      this.each(function () {
        var pluginInstance = $.data(this, pluginName);
        if (pluginInstance instanceof InCalendar && typeof pluginInstance[options] === 'function') {
          call = pluginInstance[options].apply(pluginInstance, args);
        }
      });

      return call !== undefined ? call : this;
    }
  }

}(jQuery, window, document));
