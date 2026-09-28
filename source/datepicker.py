"""Date range filter: two independent fields, each with its own calendar.

Start date and End date are separate. Changing one never moves the other.
The range is open: no day is ever disabled, so any period can be selected.
The data bounds are used only to open the calendar on a useful month and to
resolve the Full range preset.

No third party calendar package: tkcalendar is GPL-3.0 and would break the
proprietary licence settled in BRANDING-AND-LICENSE.md, so the month grid is
built here from calendar.monthcalendar().
"""
import calendar
import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta

PRESETS = ('Today', 'Yesterday', 'This week', 'This month', 'Last month', 'Full range')
WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June',
          'July', 'August', 'September', 'October', 'November', 'December')


def preset_range(name, low=None, high=None, today=None):
    """(begin, finish) for a preset. low and high are the data bounds and are
    used only by Full range. Nothing else is clamped."""
    today = today or date.today()
    if name == 'Today':
        return today, today
    if name == 'Yesterday':
        return today - timedelta(days=1), today - timedelta(days=1)
    if name == 'This week':
        a = today - timedelta(days=today.weekday())
        return a, a + timedelta(days=6)
    if name == 'This month':
        a = today.replace(day=1)
        return a, a.replace(day=calendar.monthrange(a.year, a.month)[1])
    if name == 'Last month':
        last = today.replace(day=1) - timedelta(days=1)
        return last.replace(day=1), last
    if name == 'Full range':
        return (low or today), (high or today)
    raise ValueError('Unknown preset: ' + str(name))


def install_styles(widget):
    style = ttk.Style(widget)
    try:
        style.configure('Day.TButton', padding=2, width=4)
        style.configure('DaySelected.TButton', padding=2, width=4,
                        background='#203E84', foreground='#FFFFFF')
        style.map('DaySelected.TButton', background=[('active', '#2F58AE')])
        style.configure('DayToday.TButton', padding=2, width=4, foreground='#203E84')
        style.configure('DayOther.TButton', padding=2, width=4, foreground='#8A93A5')
    except tk.TclError:
        pass


class DateDialog(tk.Toplevel):
    """One calendar for one date. Month and year navigation, today marked,
    selected day filled. Returns through on_pick when the user clicks a day."""

    def __init__(self, master, value, on_pick, translate=lambda x: x, rtl=False,
                 title='Choose date'):
        super().__init__(master)
        self.transient(master)
        self.title(translate(title))
        self.resizable(False, False)
        self.translate = translate
        self.rtl = rtl
        self.on_pick = on_pick
        self.value = value or date.today()
        self.shown = self.value.replace(day=1)
        install_styles(self)

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill='both', expand=True)

        head = ttk.Frame(outer)
        head.pack(fill='x', pady=(0, 8))
        back, forward = ('›', '‹') if rtl else ('‹', '›')
        ttk.Button(head, text=back, width=3, command=lambda: self.step(-1)).pack(side='left')
        ttk.Button(head, text=forward, width=3, command=lambda: self.step(1)).pack(side='right')

        middle = ttk.Frame(head)
        middle.pack(side='left', expand=True, fill='x')
        self.month = ttk.Combobox(middle, state='readonly', width=12,
                                  values=[translate(m) for m in MONTHS])
        self.month.pack(side='left', padx=4)
        self.month.bind('<<ComboboxSelected>>', self.jump)
        self.year = ttk.Spinbox(middle, from_=1990, to=2100, width=6, command=self.jump)
        self.year.pack(side='left', padx=4)
        self.year.bind('<Return>', self.jump)

        self.grid_frame = ttk.Frame(outer)
        self.grid_frame.pack()

        footer = ttk.Frame(outer)
        footer.pack(fill='x', pady=(10, 0))
        ttk.Button(footer, text=translate('Today'), width=10,
                   command=lambda: self.choose(date.today())).pack(side='left')
        ttk.Button(footer, text=translate('Cancel'), width=10,
                   command=self.destroy).pack(side='right')

        self.draw()
        self.bind('<Escape>', lambda e: self.destroy())
        self.grab_set()
        self.update_idletasks()
        self.geometry(f'+{master.winfo_rootx()}+{master.winfo_rooty() + master.winfo_height() + 4}')

    def jump(self, event=None):
        try:
            year = int(self.year.get())
        except ValueError:
            return
        month = self.month.current() + 1 if self.month.current() >= 0 else self.shown.month
        self.shown = date(max(1990, min(2100, year)), month, 1)
        self.draw()

    def step(self, months):
        year, month = self.shown.year, self.shown.month + months
        self.shown = date(year + (month - 1) // 12, (month - 1) % 12 + 1, 1)
        self.draw()

    def choose(self, value):
        self.on_pick(value)
        self.destroy()

    def draw(self):
        self.month.set(self.translate(MONTHS[self.shown.month - 1]))
        self.year.delete(0, 'end')
        self.year.insert(0, str(self.shown.year))
        for w in self.grid_frame.winfo_children():
            w.destroy()

        for i, name in enumerate(WEEKDAYS):
            ttk.Label(self.grid_frame, text=self.translate(name), width=4, anchor='center'
                      ).grid(row=0, column=6 - i if self.rtl else i, pady=(0, 4))

        today = date.today()
        weeks = calendar.Calendar().monthdatescalendar(self.shown.year, self.shown.month)
        for r, week in enumerate(weeks, start=1):
            for i, day in enumerate(week):
                if day == self.value:
                    style = 'DaySelected.TButton'
                elif day.month != self.shown.month:
                    style = 'DayOther.TButton'
                elif day == today:
                    style = 'DayToday.TButton'
                else:
                    style = 'Day.TButton'
                ttk.Button(self.grid_frame, text=str(day.day), style=style,
                           command=lambda v=day: self.choose(v)
                           ).grid(row=r, column=6 - i if self.rtl else i, padx=1, pady=1)


class DateField(ttk.Frame):
    """A label showing one date plus its own Calendar button."""

    def __init__(self, master, label, value, on_change, translate=lambda x: x, rtl=False):
        super().__init__(master)
        self.value = value
        self.on_change = on_change
        self.translate = translate
        self.rtl = rtl
        self.label = label
        ttk.Label(self, text=translate(label)).pack(anchor='e' if rtl else 'w')
        row = ttk.Frame(self)
        row.pack()
        self.text = tk.StringVar(value=value.isoformat())
        ttk.Label(row, textvariable=self.text, width=13, relief='sunken', padding=4,
                  anchor='center').pack(side='left')
        ttk.Button(row, text=translate('Calendar'), width=10, command=self.open).pack(side='left', padx=4)

    def open(self):
        DateDialog(self, self.value, self.set_value, self.translate, self.rtl,
                   title=self.label)

    def set_value(self, value, notify=True):
        self.value = value
        self.text.set(value.isoformat())
        if notify:
            self.on_change()


class DateRange(ttk.Frame):
    """Start date and End date as two independent fields, plus presets.

    on_change fires once, debounced, never per keystroke. An end date before the
    start date is reported inline and no query runs, rather than being silently
    swapped, so the user always sees what they actually chose.
    """

    DEBOUNCE_MS = 250

    def __init__(self, master, bounds, on_change, translate=lambda x: x, rtl=False,
                 default='Full range'):
        super().__init__(master)
        self.low, self.high = bounds if bounds else (None, None)
        self.on_change = on_change
        self.translate = translate
        self._timer = None
        install_styles(self)
        begin, finish = preset_range(default, self.low, self.high)

        self.start = DateField(self, 'Start date', begin, self.changed, translate, rtl)
        self.start.pack(side='left')
        self.end = DateField(self, 'End date', finish, self.changed, translate, rtl)
        self.end.pack(side='left', padx=(10, 0))

        presets = ttk.Frame(self)
        presets.pack(side='left', padx=(14, 0))
        ttk.Label(presets, text='').pack(anchor='w')
        strip = ttk.Frame(presets)
        strip.pack()
        for name in PRESETS:
            ttk.Button(strip, text=translate(name), width=11,
                       command=lambda n=name: self.use_preset(n)).pack(side='left', padx=1)

        self.error = tk.StringVar()
        ttk.Label(self, textvariable=self.error, foreground='#B3261E',
                  wraplength=240).pack(side='left', padx=10)
        self.bind('<Destroy>', self._cancel_timer)

    # ---------------------------------------------------------------- values

    def values(self):
        return self.start.value.isoformat(), self.end.value.isoformat()

    def valid(self):
        return self.start.value <= self.end.value

    def use_preset(self, name):
        self.set_range(*preset_range(name, self.low, self.high))

    def set_range(self, begin, finish):
        """Set both fields at once and fire a single change, so a caller that
        adjusts the period (a Monthly report widening to the whole month) does
        not trigger two queries."""
        self.start.set_value(begin, notify=False)
        self.end.set_value(finish, notify=False)
        self.changed()

    def changed(self):
        if not self.valid():
            self.error.set(self.translate('The end date is before the start date.'))
            self._cancel_timer()
            return
        self.error.set('')
        self.schedule()

    # -------------------------------------------------------------- debounce

    def schedule(self):
        self._cancel_timer()
        self._timer = self.after(self.DEBOUNCE_MS, self._fire)

    def _fire(self):
        self._timer = None
        self.on_change(*self.values())

    def _cancel_timer(self, event=None):
        if self._timer is not None:
            try:
                self.after_cancel(self._timer)
            except Exception:
                pass
            self._timer = None

    def show_error(self, message):
        self.error.set(message)
