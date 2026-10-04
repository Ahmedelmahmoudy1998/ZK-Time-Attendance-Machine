"""Shared light/dark styling. Appearance changes never rebuild data screens."""
import tkinter as tk
from tkinter import ttk

PALETTES = {
    'light': dict(bg='#EDF1F6', surface='#FFFFFF', field='#F7F9FC', text='#19263B',
                  muted='#56657A', border='#CCD5E2', hover='#E6ECF5',
                  accent='#D39340', accent_hover='#E5AA57', ink='#182130',
                  brand='#203E84', selected='#203E84', selected_text='#FFFFFF',
                  stripe='#F2F5FA', disabled='#68758A', danger='#B3261E'),
    'dark': dict(bg='#0D1118', surface='#171E29', field='#101620', text='#EDF2FA',
                 muted='#A9B7CC', border='#38465B', hover='#28364A',
                 accent='#E1AC60', accent_hover='#F0C17C', ink='#151B24',
                 brand='#E1AC60', selected='#365DA0', selected_text='#FFFFFF',
                 stripe='#1C2635', disabled='#8C9AAF', danger='#FF9B96'),
}


def calendar_styles(widget):
    root = widget._root()
    p = PALETTES.get(getattr(root, 'theme', 'light'), PALETTES['light'])
    s = ttk.Style(widget)
    for name in ('Day', 'DaySelected', 'DayToday', 'DayOther'):
        s.configure(name+'.TButton', padding=3, width=4)
    s.configure('DaySelected.TButton', background=p['accent'], foreground=p['ink'])
    s.map('DaySelected.TButton', background=[('active', p['accent_hover'])],
          foreground=[('active', p['ink'])])
    s.configure('DayToday.TButton', foreground=p['brand'], font=('Segoe UI',10,'bold'))
    s.configure('DayOther.TButton', foreground=p['muted'])


def apply_theme(root, mode):
    mode = mode if mode in PALETTES else 'light'
    root.theme = mode
    p = PALETTES[mode]
    root.colors = p
    s = ttk.Style(root)
    if s.theme_use() != 'clam':
        s.theme_use('clam')
    s.configure('.', font=('Segoe UI',10), background=p['surface'], foreground=p['text'],
                bordercolor=p['border'], lightcolor=p['border'], darkcolor=p['border'],
                troughcolor=p['bg'], selectbackground=p['selected'],
                selectforeground=p['selected_text'])
    s.configure('TFrame', background=p['surface'])
    s.configure('TLabel', background=p['surface'], foreground=p['text'])
    s.configure('Title.TLabel', font=('Segoe UI',24,'bold'), foreground=p['brand'])
    s.configure('Muted.TLabel', foreground=p['muted'])
    s.configure('Error.TLabel', foreground=p['danger'])
    s.configure('Card.TFrame', background=p['field'], borderwidth=1, relief='solid')
    s.configure('Card.TLabel', background=p['field'], foreground=p['muted'])
    s.configure('Metric.Card.TLabel', background=p['field'], foreground=p['brand'], font=('Segoe UI',28,'bold'))
    s.configure('TLabelframe', bordercolor=p['border'], relief='solid')
    s.configure('TLabelframe.Label', foreground=p['brand'], font=('Segoe UI',11,'bold'))
    s.configure('TButton', background=p['field'], foreground=p['text'], padding=(12,8),
                borderwidth=1, relief='flat', focusthickness=1, focuscolor=p['accent'])
    s.map('TButton', background=[('disabled',p['surface']),('pressed',p['border']),('active',p['hover'])],
          foreground=[('disabled',p['disabled']),('active',p['text'])],
          bordercolor=[('focus',p['accent'])])
    s.configure('Primary.TButton', background=p['accent'], foreground=p['ink'], font=('Segoe UI',10,'bold'))
    s.map('Primary.TButton', background=[('disabled',p['border']),('pressed',p['accent_hover']),('active',p['accent_hover'])],
          foreground=[('disabled',p['disabled']),('active',p['ink'])])
    for name in ('TEntry','TCombobox','TSpinbox'):
        s.configure(name, fieldbackground=p['field'], background=p['field'], foreground=p['text'],
                    insertcolor=p['text'], arrowcolor=p['text'], padding=7)
        s.map(name, fieldbackground=[('disabled',p['surface']),('readonly',p['field'])],
              foreground=[('disabled',p['disabled']),('readonly',p['text'])],
              background=[('active',p['hover'])], bordercolor=[('focus',p['accent'])],
              selectbackground=[('!disabled',p['selected'])], selectforeground=[('!disabled',p['selected_text'])])
    for name in ('TCheckbutton','TRadiobutton'):
        s.configure(name, background=p['surface'], foreground=p['text'], indicatorbackground=p['field'],
                    indicatorforeground=p['ink'], padding=5)
        s.map(name, background=[('active',p['surface'])], foreground=[('disabled',p['disabled'])],
              indicatorbackground=[('selected',p['accent']),('active',p['hover'])])
    s.configure('TNotebook', background=p['bg'], borderwidth=0, tabmargins=(0,6,0,0))
    s.configure('TNotebook.Tab', background=p['bg'], foreground=p['muted'], padding=(14,11), borderwidth=0)
    s.map('TNotebook.Tab', background=[('selected',p['surface']),('active',p['hover'])],
          foreground=[('selected',p['brand']),('active',p['text'])])
    s.configure('Treeview', rowheight=34, fieldbackground=p['surface'], background=p['surface'], foreground=p['text'], borderwidth=0)
    s.configure('Treeview.Heading', background=p['field'], foreground=p['muted'],
                font=('Segoe UI',10,'bold'), padding=(10,10), relief='flat')
    s.map('Treeview', background=[('selected',p['selected'])], foreground=[('selected',p['selected_text'])])
    s.map('Treeview.Heading', background=[('active',p['hover'])])
    for name in ('Vertical.TScrollbar','Horizontal.TScrollbar'):
        s.configure(name, background=p['border'], troughcolor=p['surface'], arrowcolor=p['muted'], borderwidth=0)
        s.map(name, background=[('active',p['muted'])])
    s.configure('TSeparator', background=p['border'])
    s.configure('TProgressbar', background=p['accent'], troughcolor=p['field'])
    root.option_add('*TCombobox*Listbox.background',p['field'])
    root.option_add('*TCombobox*Listbox.foreground',p['text'])
    root.option_add('*TCombobox*Listbox.selectBackground',p['selected'])
    root.option_add('*TCombobox*Listbox.selectForeground',p['selected_text'])
    root.option_add('*Toplevel.background',p['bg'])
    calendar_styles(root)

    def visit(w):
        if isinstance(w, (tk.Tk,tk.Toplevel)):
            w.configure(background=p['bg'])
        elif isinstance(w, tk.Canvas):
            w.configure(background=p['surface'])
        elif isinstance(w, ttk.Treeview):
            w.tag_configure('stripe', background=p['stripe'])
            w.tag_configure('total', background=p['hover'], foreground=p['text'])
        elif isinstance(w, ttk.Combobox):
            # Existing dropdown popups keep their old options unless refreshed.
            popup = root.tk.call('ttk::combobox::PopdownWindow',str(w))
            root.tk.call(str(popup)+'.f.l','configure','-background',p['field'],
                         '-foreground',p['text'],'-selectbackground',p['selected'],
                         '-selectforeground',p['selected_text'])
        for child in w.winfo_children():
            visit(child)
    visit(root)
