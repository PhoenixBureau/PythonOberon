######t['columns'] = tuple('abc')
######for a, b in zip('abc', 'ABC'):
######    t.column(a, anchor=CENTER, width=8)
######    t.heading(a, text=b, anchor=CENTER)
######t.column('#0', width=1, stretch=NO)
######t.heading('#0', text='hi', anchor=CENTER)
######
######t.insert(parent='', index=0, iid=0, text='', values=('1', '2', '3'))
######
########'0'
########t.update_idletasks()
########t.mainloop()
########Traceback (most recent call last):
########  File "<pyshell#12>", line 1, in <module>
########    t.mainloop()
########  File "/usr/local/lib/python3.8/tkinter/__init__.py", line 1429, in mainloop
########    self.tk.mainloop(n)
########KeyboardInterrupt
'''
https://stackoverflow.com/questions/16746387/display-directory-content-with-tkinter-treeview-widget
'''
import os
import tkinter as tk
import tkinter.ttk as ttk


class App(object):

    def __init__(self, master, path):
        self.nodes = dict()
        frame = tk.Frame(master)
        self.tree = ttk.Treeview(frame)
        ysb = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        xsb = ttk.Scrollbar(frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        self.tree.heading('#0', text='Project tree', anchor='w')

        self.tree.grid(sticky=tk.N+tk.S+tk.E+tk.W)
        frame.columnconfigure(0, weight=3)
        frame.rowconfigure(0, weight=3)
        ysb.grid(row=0, column=1, sticky='ns')
        xsb.grid(row=1, column=0, sticky='ew')
        frame.pack(expand=True, fill=tk.BOTH)

        abspath = os.path.abspath(path)
        self.insert_node('', abspath, abspath)
        self.tree.bind('<<TreeviewOpen>>', self.open_node)

    def insert_node(self, parent, text, abspath):
        node = self.tree.insert(parent, 'end', text=text, open=False)
        if os.path.isdir(abspath):
            self.nodes[node] = abspath
            # Insert a child node to give this node an "open arrow",
            # we have a node handy, so reuse it.  It will be deleted
            # from the children when the user clicks to open, so no
            # problem.  (It's just a little confusing.)
            self.tree.insert(node, 'end')

    def open_node(self, event):
        node = self.tree.focus()
        abspath = self.nodes.pop(node, None)
        if abspath:
            self.tree.delete(self.tree.get_children(node))
            for p in sorted(
                os.listdir(abspath),
                # Dirs first, then by name.
                key=lambda p_: (not os.path.isdir(os.path.join(abspath, p_)), p_)
                ):
                self.insert_node(node, p, os.path.join(abspath, p))


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root, path='.')
    root.mainloop()
