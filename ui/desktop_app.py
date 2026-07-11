import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from app.data_loader import load_restaurants, load_ngos
from app.optimizer_lp import pipeline_lp
from app.evaluator import evaluate
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx
import mplcursors
from math import ceil

# Color maps for priorities (dark mode friendly)
PRIORITY_COLORS = {
    5: '#ff6b6b',  # red
    4: '#ff9f43',  # orange
    3: '#ffd54f',  # yellow
    2: '#2ecc71',  # green
    1: '#4aa3ff'   # blue
}
RESTAURANT_COLOR = '#7f8c8d'  # grey

class DesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Food Wastage Allocator - Desktop (LP) - Dark Mode")
        self.geometry("1200x760")
        self.configure(bg='#121212')
        self.style = ttk.Style(self)
        # ttk theme adjustments
        try:
            self.style.theme_use('clam')
        except Exception:
            pass
        self.style.configure('TLabel', background='#121212', foreground='white')
        self.style.configure('TButton', background='#1f1f1f', foreground='white')
        self.style.configure('TEntry', fieldbackground='#2b2b2b', foreground='white')
        self.alpha = tk.DoubleVar(value=0.4)
        self.create_widgets()
        # Load default data
        try:
            self.R = load_restaurants("data/restaurants.csv")
            self.N = load_ngos("data/ngos.csv")
        except Exception as e:
            messagebox.showerror("Data load error", str(e))
            self.R, self.N = [], []

    def create_widgets(self):
        top = ttk.Frame(self)
        top.pack(fill='x', padx=8, pady=6)

        ttk.Label(top, text="Priority weight α:", foreground='white').pack(side='left')
        ttk.Entry(top, textvariable=self.alpha, width=6).pack(side='left', padx=4)
        ttk.Button(top, text="Run LP", command=self.run_lp).pack(side='left', padx=6)
        ttk.Button(top, text="Export CSV", command=self.export_csv).pack(side='left', padx=6)
        ttk.Button(top, text="Open Map", command=self.open_map).pack(side='left', padx=6)

        ttk.Button(top, text="Load Restaurants CSV", command=self.load_restaurants).pack(side='left', padx=6)
        ttk.Button(top, text="Load NGOs CSV", command=self.load_ngos).pack(side='left', padx=6)

        # Left panel: text summary and allocations
        left = ttk.Frame(self)
        left.pack(side='left', fill='y', padx=8, pady=6)

        self.summary_text = tk.Text(left, width=45, height=18, bg='#1e1e1e', fg='white')
        self.summary_text.pack(padx=4, pady=4)

        self.alloc_tree = ttk.Treeview(left, columns=("R","N","Amount","Cost"), show='headings', height=18)
        for c in ("R","N","Amount","Cost"):
            self.alloc_tree.heading(c, text=c)
        self.alloc_tree.pack(padx=4, pady=4)

        # Right panel: visualizations (matplotlib)
        right = ttk.Frame(self)
        right.pack(side='left', fill='both', expand=True, padx=8, pady=6)

        # Figure 1: fill ratios bar chart (dark background)
        self.fig1 = plt.Figure(figsize=(6,3), facecolor='#121212')
        self.ax1 = self.fig1.add_subplot(111)
        self.ax1.set_facecolor('#121212')
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=right)
        self.canvas1.get_tk_widget().pack(side='top', fill='both', expand=True)

        # Figure 2: bipartite graph (dark)
        self.fig2 = plt.Figure(figsize=(6,4), facecolor='#121212')
        self.ax2 = self.fig2.add_subplot(111)
        self.ax2.set_facecolor('#121212')
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=right)
        self.canvas2.get_tk_widget().pack(side='top', fill='both', expand=True)

        # Map preview panel (static snapshot)
        self.fig3 = plt.Figure(figsize=(6,3), facecolor='#121212')
        self.ax3 = self.fig3.add_subplot(111)
        self.ax3.set_facecolor('#121212')
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=right)
        self.canvas3.get_tk_widget().pack(side='top', fill='both', expand=True)

    def load_restaurants(self):
        path = filedialog.askopenfilename(title="Select restaurants CSV", filetypes=[("CSV","*.csv")])
        if path:
            try:
                self.R = load_restaurants(path)
                messagebox.showinfo("Loaded", f"Loaded {len(self.R)} restaurants")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def load_ngos(self):
        path = filedialog.askopenfilename(title="Select NGOs CSV", filetypes=[("CSV","*.csv")])
        if path:
            try:
                self.N = load_ngos(path)
                messagebox.showinfo("Loaded", f"Loaded {len(self.N)} NGOs")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def run_lp(self):
        if not self.R or not self.N:
            messagebox.showwarning("No data", "Load restaurants and NGOs CSV first.")
            return
        alpha = float(self.alpha.get())
        try:
            allocs = pipeline_lp(self.R, self.N, alpha=alpha)
        except Exception as e:
            messagebox.showerror("LP error", str(e))
            return
        metrics = evaluate(self.R, self.N, allocs)
        self.show_summary(metrics)
        self.show_allocations(allocs)
        self.plot_fill_ratios(allocs)
        self.plot_bipartite(allocs)

    def show_summary(self, metrics):
        self.summary_text.delete("1.0", tk.END)
        for k,v in metrics.items():
            self.summary_text.insert(tk.END, f"{k}: {v}\n")

    def show_allocations(self, allocs):
        for item in self.alloc_tree.get_children():
            self.alloc_tree.delete(item)
        for a in allocs:
            self.alloc_tree.insert("", tk.END, values=(a.restaurant_id, a.ngo_id, a.amount, f"{a.cost_per_unit:.2f}"))

    def plot_fill_ratios(self, allocs):
        recv = {n.id:0 for n in self.N}
        for a in allocs:
            recv[a.ngo_id] += a.amount
        labels = [n.id for n in self.N]
        ratios = []
        colors = []
        for n in self.N:
            if n.demand>0:
                ratios.append(min(1.0, recv[n.id]/n.demand))
            else:
                ratios.append(1.0)
            colors.append(PRIORITY_COLORS.get(n.priority, '#ffffff'))

        self.ax1.clear()
        bars = self.ax1.bar(labels, ratios, color=colors, edgecolor='#222222')
        self.ax1.set_ylim(0,1.05)
        self.ax1.set_ylabel("Fill ratio", color='white')
        self.ax1.set_title("NGO fill ratios", color='white')
        self.ax1.tick_params(colors='white')
        # add legend mapping colors to priorities
        handles = []
        seen = []
        for p, col in sorted(PRIORITY_COLORS.items(), reverse=True):
            handles.append(plt.Line2D([0],[0], marker='s', color=col, markersize=8, linestyle=''))
            seen.append(f"Priority {p}")
        self.ax1.legend(handles, [f"Priority {p}" for p in sorted(PRIORITY_COLORS.keys(), reverse=True)], facecolor='#1e1e1e', edgecolor='white', labelcolor='white')

        # mplcursors for tooltips on bars
        cursor = mplcursors.cursor(bars, hover=True)
        @cursor.connect("add")
        def _(sel):
            idx = int(sel.index)
            n = self.N[idx]
            recv_amt = recv[n.id]
            sel.annotation.set_text(f"{n.id}\\nPriority: {n.priority}\\nDemand: {n.demand}\\nReceived: {recv_amt}\\nFill: {ratios[idx]:.2f}")
            sel.annotation.get_bbox_patch().set(fc="#2b2b2b", ec="white")
            sel.annotation.set_color("white")
        self.canvas1.draw()

    
    def plot_bipartite(self, allocs):
        self.ax2.clear()
        import networkx as nx
        G = nx.DiGraph()

        # Nodes
        for r in self.R:
            G.add_node(r.id, bipartite=0)
        for n in self.N:
            G.add_node(n.id, bipartite=1)

        # Edges
        for a in allocs:
            G.add_edge(a.restaurant_id, a.ngo_id, weight=max(1, a.amount))

        # Positions
        left = [r.id for r in self.R]
        right = [n.id for n in self.N]
        pos = {}
        for i,n in enumerate(left):
            pos[n] = (0,-i)
        for i,n in enumerate(right):
            pos[n] = (1,-i)

        # Neon node colors
        node_colors = []
        for node in G.nodes():
            if node in left:
                node_colors.append("#66d9ff")  # neon cyan
            else:
                pr = next(n.priority for n in self.N if n.id == node)
                bright = {5:"#ff4d4d",4:"#ff8533",3:"#ffd633",2:"#33ff99",1:"#4da6ff"}
                node_colors.append(bright.get(pr,"#ffffff"))

        # Neon edge colors + thickness
        max_amt = max((G[u][v]['weight'] for u,v in G.edges()), default=1)
        edge_colors=[]
        edge_widths=[]
        for u,v in G.edges():
            amt = G[u][v]['weight']
            ratio = amt/max_amt
            # neon cyan → neon pink
            r = ratio
            g = 0
            b = 1 - ratio
            edge_colors.append((r,g,b))
            edge_widths.append(1 + ratio*4)

        nx.draw(
            G, pos, ax=self.ax2,
            node_size=900, node_color=node_colors,
            edge_color=edge_colors, width=edge_widths,
            with_labels=True, font_color="white"
        )

        # Edge labels with black outline
        edge_labels = {(u,v): G[u][v]['weight'] for u,v in G.edges()}
        nx.draw_networkx_edge_labels(
            G, pos, ax=self.ax2, edge_labels=edge_labels,
            font_color="white",
            bbox=dict(facecolor="black", edgecolor="none", alpha=0.7)
        )

        self.ax2.set_title("Allocations (Neon Style)", color="white")
        self.canvas2.draw()


    
    def open_map(self):
        # generate folium map and open in browser; also update preview snapshot in GUI
        try:
            from ui.map_generator import generate_map_with_heatmap
        except Exception as e:
            messagebox.showerror("Map Error", f"Cannot import map generator: {e}")
            return
        out = os.path.join(os.getcwd(), "map.html")
        try:
            generate_map_with_heatmap(out_path=out, alpha=float(self.alpha.get()))
        except Exception as e:
            messagebox.showerror("Map Error", str(e))
            return
        # open in default browser
        import webbrowser
        webbrowser.open('file://' + out)
        # create a simple static preview snapshot using matplotlib (scatter + lines)
        try:
            self.create_map_preview()
        except Exception as e:
            print("Preview generation failed:", e)

    def export_csv(self):
        allocs = []
        for iid in self.alloc_tree.get_children():
            vals = self.alloc_tree.item(iid)['values']
            allocs.append(tuple(vals))
        if not allocs:
            messagebox.showwarning("No allocations", "Run LP first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("restaurant_id,ngo_id,amount,cost_per_unit\n")
                for r,n,amt,cost in allocs:
                    f.write(f"{r},{n},{amt},{cost}\n")
            messagebox.showinfo("Exported", f"Allocations exported to {path}")


    def create_map_preview(self):
        # static matplotlib preview: plot restaurants, NGOs and allocation lines (no basemap)
        try:
            allocs = pipeline_lp(self.R, self.N, alpha=float(self.alpha.get()))
        except Exception as e:
            messagebox.showerror("LP error", str(e))
            return
        self.ax3.clear()
        # draw restaurants and ngos
        r_lats = [r.lat for r in self.R]
        r_lons = [r.lon for r in self.R]
        n_lats = [n.lat for n in self.N]
        n_lons = [n.lon for n in self.N]
        self.ax3.scatter(r_lons, r_lats, c=RESTAURANT_COLOR, s=80, label='Restaurants', edgecolors='white')
        # NGO colors by priority
        ngo_colors = [PRIORITY_COLORS.get(n.priority, '#ffffff') for n in self.N]
        for n, col in zip(self.N, ngo_colors):
            self.ax3.scatter(n.lon, n.lat, c=col, s=120, marker='s', edgecolors='white')
            self.ax3.text(n.lon+0.001, n.lat+0.001, n.id, color='white', fontsize=9)

        # draw lines for allocations
        for a in allocs:
            r = next((x for x in self.R if x.id==a.restaurant_id), None)
            n = next((x for x in self.N if x.id==a.ngo_id), None)
            if r and n:
                lw = max(0.5, a.amount/10.0)
                self.ax3.plot([r.lon, n.lon], [r.lat, n.lat], color='cyan', linewidth=lw, alpha=0.7)
        self.ax3.set_xlabel("Longitude", color='white')
        self.ax3.set_ylabel("Latitude", color='white')
        self.ax3.set_title("Map Preview (static)", color='white')
        self.ax3.tick_params(colors='white')

        # add matplotlib legend for node colors and restaurants
        # create custom legend handles
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        legend_handles = []
        # priority patches
        for p in sorted(set(n.priority for n in self.N), reverse=True):
            color = PRIORITY_COLORS.get(p, '#ffffff')
            legend_handles.append(Patch(facecolor=color, edgecolor='white', label=f'Priority {p}'))
        # restaurant handle
        legend_handles.append(Line2D([0],[0], marker='o', color='w', label='Restaurant', markerfacecolor=RESTAURANT_COLOR, markersize=8))
        # add legend to ax3
        self.ax3.legend(handles=legend_handles, loc='lower left', facecolor='#1e1e1e', edgecolor='white', fontsize=9)

        self.canvas3.draw()

if __name__ == "__main__":
    app = DesktopApp()
    app.mainloop()
