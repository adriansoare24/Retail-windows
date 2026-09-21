import sqlite3, shutil, os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

DB="retail_v2.db"

def conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init():
    c=conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY, barcode TEXT UNIQUE, name TEXT NOT NULL,
      category TEXT, unit TEXT DEFAULT 'buc', buy REAL DEFAULT 0,
      price REAL DEFAULT 0, stock REAL DEFAULT 0, min_stock REAL DEFAULT 0,
      vat REAL DEFAULT 21, active INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS suppliers(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, cui TEXT, phone TEXT, email TEXT, address TEXT);
    CREATE TABLE IF NOT EXISTS customers(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT);
    CREATE TABLE IF NOT EXISTS purchases(
      id INTEGER PRIMARY KEY, created TEXT, supplier TEXT, total REAL);
    CREATE TABLE IF NOT EXISTS purchase_items(
      id INTEGER PRIMARY KEY, purchase_id INTEGER, product_id INTEGER,
      qty REAL, buy_price REAL, FOREIGN KEY(purchase_id) REFERENCES purchases(id),
      FOREIGN KEY(product_id) REFERENCES products(id));
    CREATE TABLE IF NOT EXISTS sales(
      id INTEGER PRIMARY KEY, created TEXT, total REAL, payment TEXT, customer TEXT,
      discount REAL DEFAULT 0, returned INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS sale_items(
      id INTEGER PRIMARY KEY, sale_id INTEGER, product_id INTEGER,
      qty REAL, price REAL, FOREIGN KEY(sale_id) REFERENCES sales(id),
      FOREIGN KEY(product_id) REFERENCES products(id));
    CREATE TABLE IF NOT EXISTS movements(
      id INTEGER PRIMARY KEY, created TEXT, product_id INTEGER,
      kind TEXT, qty REAL, note TEXT);
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT);
    CREATE TABLE IF NOT EXISTS settings(
      key TEXT PRIMARY KEY, value TEXT);
    """)
    if not c.execute("SELECT 1 FROM users").fetchone():
        c.execute("INSERT INTO users(username,password,role) VALUES('admin','admin','Administrator')")
    c.commit(); c.close()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        super().title("Retail Windows V2")
        self.geometry("1280x760")
        self.minsize(1100,650)
        self.cart=[]
        self.make_ui()
        self.dashboard()

    def make_ui(self):
        s=ttk.Style(self); s.theme_use("clam")
        nav=ttk.Frame(self,padding=10); nav.pack(side="left",fill="y")
        ttk.Label(nav,text="RETAIL",font=("Segoe UI",23,"bold")).pack(pady=(8,25))
        items=[
          ("Dashboard",self.dashboard),("POS / Vanzare",self.pos),
          ("Produse",self.products),("Recepție marfă",self.purchases),
          ("Furnizori",self.suppliers),("Clienți",self.customers),
          ("Inventar",self.inventory),("Retururi",self.returns),
          ("Rapoarte",self.reports),("Utilizatori",self.users),
          ("Backup",self.backup),("Setări",self.settings)]
        for t,f in items: ttk.Button(nav,text=t,command=f,width=23).pack(fill="x",pady=2)
        self.main=ttk.Frame(self,padding=18); self.main.pack(side="left",fill="both",expand=True)

    def clear(self):
        for w in self.main.winfo_children(): w.destroy()
    def title(self,t):
        self.clear(); ttk.Label(self.main,text=t,font=("Segoe UI",24,"bold")).pack(anchor="w",pady=(0,14))

    def dashboard(self):
        self.title("Dashboard")
        c=conn()
        vals=[
          ("Vânzări azi",c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(created)=date('now','localtime') AND returned=0").fetchone()[0]),
          ("Bonuri azi",c.execute("SELECT COUNT(*) FROM sales WHERE date(created)=date('now','localtime')").fetchone()[0]),
          ("Produse",c.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0]),
          ("Stoc redus",c.execute("SELECT COUNT(*) FROM products WHERE active=1 AND stock<=min_stock").fetchone()[0])]
        c.close()
        row=ttk.Frame(self.main);row.pack(fill="x")
        for name,val in vals:
            f=ttk.LabelFrame(row,text=name,padding=22);f.pack(side="left",fill="x",expand=True,padx=4)
            text=f"{val:.2f} lei" if isinstance(val,float) else str(val)
            ttk.Label(f,text=text,font=("Segoe UI",19,"bold")).pack()
        ttk.Label(self.main,text="\nV2 include POS, recepții, retururi, discount, inventar, rapoarte și backup. Casa de marcat nu este conectată.",font=("Segoe UI",11)).pack(anchor="w")

    def products(self):
        self.title("Produse")
        form=ttk.Frame(self.main);form.pack(fill="x")
        vs=[tk.StringVar() for _ in range(8)]
        labs=["Cod bare","Denumire","Categorie","Unitate","Achiziție","Vânzare","Stoc","Minim"]
        for i,(l,v) in enumerate(zip(labs,vs)):
            ttk.Label(form,text=l).grid(row=0,column=i,padx=2)
            ttk.Entry(form,textvariable=v,width=14).grid(row=1,column=i,padx=2)
        tree=self.table(("id","barcode","name","category","unit","buy","price","stock","min"),("ID","Cod","Denumire","Categorie","UM","Achiziție","Vânzare","Stoc","Minim"))
        def load():
            for x in tree.get_children():tree.delete(x)
            c=conn()
            for r in c.execute("SELECT id,barcode,name,category,unit,buy,price,stock,min_stock FROM products WHERE active=1 ORDER BY name"):
                tree.insert("", "end", values=tuple(r))
            c.close()
        def add():
            try:
                c=conn();c.execute("""INSERT INTO products(barcode,name,category,unit,buy,price,stock,min_stock)
                VALUES(?,?,?,?,?,?,?,?)""",(vs[0].get(),vs[1].get(),vs[2].get(),vs[3].get() or "buc",
                float(vs[4].get() or 0),float(vs[5].get() or 0),float(vs[6].get() or 0),float(vs[7].get() or 0)))
                c.commit();c.close();load()
                for v in vs:v.set("")
            except Exception as e: messagebox.showerror("Eroare",str(e))
        ttk.Button(form,text="Adaugă produs",command=add).grid(row=1,column=8,padx=8)
        ttk.Button(self.main,text="Dezactivează produs selectat",command=lambda:self.delete_product(tree,load)).pack(anchor="e",pady=5)
        load()

    def delete_product(self,tree,load):
        s=tree.selection()
        if not s:return
        pid=tree.item(s[0])["values"][0]
        if messagebox.askyesno("Confirmare","Dezactivezi produsul?"):
            c=conn();c.execute("UPDATE products SET active=0 WHERE id=?",(pid,));c.commit();c.close();load()

    def table(self,cols,heads):
        t=ttk.Treeview(self.main,columns=cols,show="headings")
        for c,h in zip(cols,heads):t.heading(c,text=h);t.column(c,width=115)
        t.pack(fill="both",expand=True,pady=12);return t

    def pos(self):
        self.title("POS / Vânzare")
        left=ttk.Frame(self.main);left.pack(side="left",fill="both",expand=True,padx=(0,10))
        right=ttk.LabelFrame(self.main,text="Coș",padding=10);right.pack(side="right",fill="both",expand=True)
        q=tk.StringVar(); ttk.Label(left,text="Scanează codul sau caută produsul").pack(anchor="w")
        ttk.Entry(left,textvariable=q).pack(fill="x")
        tree=ttk.Treeview(left,columns=("id","barcode","name","price","stock"),show="headings")
        for x,h in zip(("id","barcode","name","price","stock"),("ID","Cod","Produs","Preț","Stoc")):tree.heading(x,text=h)
        tree.pack(fill="both",expand=True,pady=8)
        cart=ttk.Treeview(right,columns=("name","qty","price","total"),show="headings")
        for x,h in zip(("name","qty","price","total"),("Produs","Cant.","Preț","Total")):cart.heading(x,text=h)
        cart.pack(fill="both",expand=True)
        discount=tk.DoubleVar(value=0); total=tk.StringVar(value="Total: 0.00 lei")
        ttk.Label(right,text="Discount %").pack(anchor="w")
        ttk.Spinbox(right,from_=0,to=100,textvariable=discount,width=8).pack(anchor="w")
        ttk.Label(right,textvariable=total,font=("Segoe UI",19,"bold")).pack(pady=8)
        pay=tk.StringVar(value="Numerar")
        ttk.Combobox(right,textvariable=pay,values=["Numerar","Card","Transfer"],state="readonly").pack(fill="x")
        def refresh(*a):
            for x in tree.get_children():tree.delete(x)
            c=conn();term=q.get().strip()
            for r in c.execute("""SELECT id,barcode,name,price,stock FROM products
                WHERE active=1 AND (barcode LIKE ? OR name LIKE ?) ORDER BY name LIMIT 100""",(f"%{term}%",f"%{term}%")):
                tree.insert("", "end",values=tuple(r))
            c.close()
        def redraw():
            for x in cart.get_children():cart.delete(x)
            sub=sum(x["price"]*x["qty"] for x in self.cart)
            disc=sub*max(0,min(100,discount.get()))/100
            for x in self.cart:cart.insert("", "end",values=(x["name"],x["qty"],f"{x['price']:.2f}",f"{x['price']*x['qty']:.2f}"))
            total.set(f"Total: {sub-disc:.2f} lei")
        def add():
            s=tree.selection()
            if not s:return
            v=tree.item(s[0])["values"]
            for x in self.cart:
                if x["id"]==int(v[0]):x["qty"]+=1;break
            else:self.cart.append({"id":int(v[0]),"name":v[2],"price":float(v[3]),"qty":1})
            redraw()
        def remove():
            s=cart.selection()
            if not s:return
            name=cart.item(s[0])["values"][0]
            self.cart=[x for x in self.cart if x["name"]!=name];redraw()
        def checkout():
            if not self.cart:return
            sub=sum(x["price"]*x["qty"] for x in self.cart);disc=sub*discount.get()/100;grand=sub-disc
            c=conn()
            try:
                c.execute("BEGIN")
                sid=c.execute("INSERT INTO sales(created,total,payment,discount,customer) VALUES(?,?,?,?,?)",
                               (datetime.now().isoformat(timespec="seconds"),grand,pay.get(),disc,"")).lastrowid
                for x in self.cart:
                    stock=c.execute("SELECT stock FROM products WHERE id=?",(x["id"],)).fetchone()[0]
                    if stock<x["qty"]:raise ValueError("Stoc insuficient pentru "+x["name"])
                    c.execute("INSERT INTO sale_items(sale_id,product_id,qty,price) VALUES(?,?,?,?)",(sid,x["id"],x["qty"],x["price"]))
                    c.execute("UPDATE products SET stock=stock-? WHERE id=?",(x["qty"],x["id"]))
                    c.execute("INSERT INTO movements(created,product_id,kind,qty,note) VALUES(?,?,?,?,?)",
                              (datetime.now().isoformat(timespec="seconds"),x["id"],"Vânzare",-x["qty"],f"Bon #{sid}"))
                c.commit();self.cart.clear();redraw();messagebox.showinfo("Vânzare",f"Bon #{sid} înregistrat.\nTotal: {grand:.2f} lei")
            except Exception as e:c.rollback();messagebox.showerror("Eroare",str(e))
            finally:c.close()
        q.trace_add("write",refresh);tree.bind("<Double-1>",lambda e:add())
        ttk.Button(left,text="Adaugă în coș",command=add).pack(anchor="e")
        ttk.Button(right,text="Elimină produs",command=remove).pack(fill="x")
        ttk.Button(right,text="ÎNCASARE",command=checkout).pack(fill="x",pady=5)
        refresh()

    def purchases(self):
        self.title("Recepție marfă")
        form=ttk.Frame(self.main);form.pack(fill="x")
        barcode=tk.StringVar();qty=tk.DoubleVar(value=1);price=tk.DoubleVar(value=0)
        ttk.Label(form,text="Cod produs").grid(row=0,column=0);ttk.Entry(form,textvariable=barcode).grid(row=1,column=0)
        ttk.Label(form,text="Cantitate").grid(row=0,column=1);ttk.Entry(form,textvariable=qty).grid(row=1,column=1)
        ttk.Label(form,text="Preț achiziție").grid(row=0,column=2);ttk.Entry(form,textvariable=price).grid(row=1,column=2)
        supplier=tk.StringVar();ttk.Label(form,text="Furnizor").grid(row=0,column=3);ttk.Entry(form,textvariable=supplier,width=25).grid(row=1,column=3)
        def receive():
            c=conn();p=c.execute("SELECT id FROM products WHERE barcode=? AND active=1",(barcode.get(),)).fetchone()
            if not p: c.close();messagebox.showerror("Eroare","Produsul nu există.");return
            try:
                c.execute("BEGIN")
                total=qty.get()*price.get()
                pid=c.execute("INSERT INTO purchases(created,supplier,total) VALUES(?,?,?)",(datetime.now().isoformat(timespec="seconds"),supplier.get(),total)).lastrowid
                c.execute("INSERT INTO purchase_items(purchase_id,product_id,qty,buy_price) VALUES(?,?,?,?)",(pid,p["id"],qty.get(),price.get()))
                c.execute("UPDATE products SET stock=stock+?,buy=? WHERE id=?",(qty.get(),price.get(),p["id"]))
                c.execute("INSERT INTO movements(created,product_id,kind,qty,note) VALUES(?,?,?,?,?)",(datetime.now().isoformat(timespec="seconds"),p["id"],"Recepție",qty.get(),f"Recepție #{pid}"))
                c.commit();messagebox.showinfo("Recepție","Marfa a fost recepționată.")
            except Exception as e:c.rollback();messagebox.showerror("Eroare",str(e))
            finally:c.close()
        ttk.Button(form,text="RECEPȚIONEAZĂ",command=receive).grid(row=1,column=4,padx=10)

    def suppliers(self): self.generic("Furnizori","suppliers",("id","name","cui","phone","email"),("ID","Nume","CUI","Telefon","Email"))
    def customers(self): self.generic("Clienți","customers",("id","name","phone","email"),("ID","Nume","Telefon","Email"))
    def generic(self,title,table,cols,heads):
        self.title(title);self.table(cols,heads)
        # list refresh intentionally simple for V2
        t=self.main.winfo_children()[-1];c=conn()
        for r in c.execute(f"SELECT {','.join(cols)} FROM {table} ORDER BY id DESC"):t.insert("", "end",values=tuple(r))
        c.close()

    def inventory(self):
        self.title("Inventar")
        t=self.table(("id","barcode","name","stock","min"),("ID","Cod","Produs","Stoc","Minim"))
        c=conn()
        for r in c.execute("SELECT id,barcode,name,stock,min_stock FROM products WHERE active=1 ORDER BY name"):t.insert("", "end",values=tuple(r))
        c.close()

    def returns(self):
        self.title("Retururi")
        ttk.Label(self.main,text="În V2 returul se operează prin selectarea unui bon și refacerea stocului.").pack(anchor="w")
        t=self.table(("id","created","total","payment","returned"),("Bon","Data","Total","Plată","Returnat"))
        c=conn()
        for r in c.execute("SELECT id,created,total,payment,returned FROM sales ORDER BY id DESC LIMIT 200"):t.insert("", "end",values=tuple(r))
        c.close()
        def ret():
            s=t.selection()
            if not s:return
            sid=int(t.item(s[0])["values"][0])
            c=conn()
            if c.execute("SELECT returned FROM sales WHERE id=?",(sid,)).fetchone()[0]:
                c.close();messagebox.showwarning("Retur","Bonul este deja returnat.");return
            if messagebox.askyesno("Retur",f"Returnezi bonul #{sid}?"):
                c.execute("SELECT product_id,qty FROM sale_items WHERE sale_id=?",(sid,))
                for r in c.fetchall():c.execute("UPDATE products SET stock=stock+? WHERE id=?",(r["qty"],r["product_id"]))
                c.execute("UPDATE sales SET returned=1 WHERE id=?",(sid,));c.commit();c.close();messagebox.showinfo("Retur","Retur înregistrat.");self.returns()
            else:c.close()
        ttk.Button(self.main,text="Returnează bonul selectat",command=ret).pack(anchor="e")

    def reports(self):
        self.title("Rapoarte")
        c=conn()
        sales=c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE returned=0").fetchone()[0]
        purchases=c.execute("SELECT COALESCE(SUM(total),0) FROM purchases").fetchone()[0]
        profit=c.execute("""SELECT COALESCE(SUM((si.price-p.buy)*si.qty),0) FROM sale_items si
                            JOIN products p ON p.id=si.product_id JOIN sales s ON s.id=si.sale_id WHERE s.returned=0""").fetchone()[0]
        c.close()
        for a,b in [("Vânzări",sales),("Achiziții",purchases),("Profit brut estimat",profit)]:
            f=ttk.LabelFrame(self.main,text=a,padding=18);f.pack(fill="x",pady=5)
            ttk.Label(f,text=f"{b:.2f} lei",font=("Segoe UI",17,"bold")).pack(anchor="w")

    def users(self): self.generic("Utilizatori","users",("id","username","role"),("ID","Utilizator","Rol"))
    def backup(self):
        self.title("Backup / Restaurare")
        ttk.Label(self.main,text="Baza de date este locală. Fă backup periodic.").pack(anchor="w")
        def b():
            p=filedialog.asksaveasfilename(defaultextension=".db",initialfile=f"retail_v2_{datetime.now():%Y%m%d_%H%M}.db")
            if p:shutil.copy2(DB,p);messagebox.showinfo("Backup","Backup creat.")
        def r():
            p=filedialog.askopenfilename(filetypes=[("Database","*.db")])
            if p and messagebox.askyesno("Restaurare","Înlocuiești baza actuală?"):
                shutil.copy2(p,DB);messagebox.showinfo("Restaurare","Baza a fost restaurată. Repornește programul.")
        ttk.Button(self.main,text="Creează backup",command=b).pack(pady=8)
        ttk.Button(self.main,text="Restaurează backup",command=r).pack(pady=8)
    def settings(self):
        self.title("Setări")
        ttk.Label(self.main,text="Retail Windows V2",font=("Segoe UI",14,"bold")).pack(anchor="w")
        ttk.Label(self.main,text="Casa de marcat fiscală: neconectată.").pack(anchor="w",pady=5)
        ttk.Label(self.main,text="Utilizator implicit: admin / admin (schimbă parola înainte de utilizare reală).").pack(anchor="w")

if __name__=="__main__":
    init();App().mainloop()
