from tkinter import *
from tkinter import ttk
from tkinter import colorchooser
from PIL import Image, ImageDraw, ImageTk
import io

CANVAS_W = 1280
CANVAS_H = 720

# ── Flood fill em imagem PIL ──────────────────────────────────────────────────
def renderizar_imagem_figuras(figuras_lista):
    """Desenha todas as figuras em uma imagem PIL e retorna o objeto Image."""
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    draw = ImageDraw.Draw(img)
    for (fig, values), cor_linha, _ in figuras_lista:
        r, g, b = hex_to_rgb(cor_linha)
        if fig == "linha":
            draw.line([values[0], values[1], values[2], values[3]], fill=(r, g, b), width=2)
        else:  # rabisco
            if len(values) >= 2:
                draw.line(values, fill=(r, g, b), width=2)
    return img

def flood_fill_pil(img, x, y, fill_color_rgb):
    """Aplica flood fill na imagem PIL a partir do ponto (x, y)."""
    img = img.convert("RGB")
    pixels = img.load()
    target = pixels[x, y]

    fr, fg, fb = fill_color_rgb
    if target == (fr, fg, fb):
        return img

    stack = [(x, y)]
    visited = set()
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in visited:
            continue
        if cx < 0 or cx >= CANVAS_W or cy < 0 or cy >= CANVAS_H:
            continue
        if pixels[cx, cy] != target:
            continue
        pixels[cx, cy] = (fr, fg, fb)
        visited.add((cx, cy))
        stack.extend([(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)])
    return img

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# ── Estado global ──────────────────────────────────────────────────────────────
figuras = []        # lista de ((fig, values), cor_linha, cor_fill)
undo_stack = []     # figuras removidas para poder refazer
figura_nova = None
imagem_base = None  # Image PIL com todas as figuras sem fill ativo
tk_img_ref = None   # referência para evitar garbage collect

# ── Callbacks de desenho ───────────────────────────────────────────────────────
def iniciar_figura_nova(event):
    global figura_nova
    if tipo_figura_var.get() == 'Linha':
        figura_nova = ("linha", (event.x, event.y, event.x, event.y))
    else:
        figura_nova = ("rabisco", [(event.x, event.y)])

def atualizar_figura_nova(event):
    global figura_nova
    if figura_nova[0] == "rabisco":
        figura_nova[1].append((event.x, event.y))
    else:
        figura_nova = ("linha", (figura_nova[1][0], figura_nova[1][1], event.x, event.y))
    desenhar_figuras()
    desenhar_figura_nova()

def incluir_figura_nova(event):
    if not incompleta(figura_nova):
        cor_linha = cor_linha_var.get()
        preenchido = preenchido_var.get() == 'Sim'
        cor_fill = cor_fill_var.get() if preenchido else None
        figuras.append(((figura_nova[0], figura_nova[1]), cor_linha, cor_fill))
        undo_stack.clear()  # nova ação descarta o histórico de redo
        aplicar_fills()
    else:
        desenhar_figuras()

def desfazer(event=None):
    if figuras:
        undo_stack.append(figuras.pop())
        aplicar_fills() if figuras else desenhar_figuras()

def refazer(event=None):
    if undo_stack:
        figuras.append(undo_stack.pop())
        aplicar_fills()

def desenhar_figuras():
    """Redesenha só as linhas no canvas (sem fills)."""
    global tk_img_ref
    img = renderizar_imagem_figuras(figuras)
    tk_img_ref = ImageTk.PhotoImage(img)
    canvas.delete("all")
    canvas.create_image(0, 0, anchor=NW, image=tk_img_ref)

def desenhar_figura_nova():
    """Desenha a linha/rabisco em andamento (tracejado) por cima."""
    fig, values = figura_nova
    cor_linha = cor_linha_var.get()
    if fig == "linha":
        canvas.create_line(values[0], values[1], values[2], values[3],
                           dash=(4, 2), fill=cor_linha, width=2)
    else:
        if len(values) >= 2:
            canvas.create_line(values, dash=(4, 2), fill=cor_linha, width=2)

def aplicar_fills():
    """Renderiza todas as linhas em PIL e aplica os flood fills acumulados."""
    global tk_img_ref
    img = renderizar_imagem_figuras(figuras)
    for (fig, values), cor_linha, cor_fill in figuras:
        if cor_fill is None:
            continue
        # ponto de semente: centro da linha ou centroide do rabisco
        if fig == "linha":
            seed_x = (values[0] + values[2]) // 2
            seed_y = (values[1] + values[3]) // 2 + 5  # ligeiramente abaixo
        else:
            xs = [p[0] for p in values]
            ys = [p[1] for p in values]
            seed_x = sum(xs) // len(xs)
            seed_y = sum(ys) // len(ys)
        seed_x = max(0, min(CANVAS_W - 1, seed_x))
        seed_y = max(0, min(CANVAS_H - 1, seed_y))
        fill_rgb = hex_to_rgb(cor_fill)
        img = flood_fill_pil(img, seed_x, seed_y, fill_rgb)
    # redesenha as linhas por cima do fill
    draw = ImageDraw.Draw(img)
    for (fig, values), cor_linha, _ in figuras:
        r, g, b = hex_to_rgb(cor_linha)
        if fig == "linha":
            draw.line([values[0], values[1], values[2], values[3]], fill=(r, g, b), width=2)
        else:
            if len(values) >= 2:
                draw.line(values, fill=(r, g, b), width=2)
    tk_img_ref = ImageTk.PhotoImage(img)
    canvas.delete("all")
    canvas.create_image(0, 0, anchor=NW, image=tk_img_ref)

def incompleta(figura):
    fig, values = figura
    if fig == "linha":
        return (values[0], values[1]) == (values[2], values[3])
    else:
        return len(values) <= 1

# ── Escolha de cores ───────────────────────────────────────────────────────────
def escolher_cor_linha():
    cor = colorchooser.askcolor(color=cor_linha_var.get(), title="Cor da linha")
    if cor[1]:
        cor_linha_var.set(cor[1])
        btn_cor_linha.config(bg=cor[1])

def escolher_cor_fill():
    cor = colorchooser.askcolor(color=cor_fill_var.get(), title="Cor de preenchimento")
    if cor[1]:
        cor_fill_var.set(cor[1])
        btn_cor_fill.config(bg=cor[1])

def atualizar_estado_fill(*args):
    estado = NORMAL if preenchido_var.get() == 'Sim' else DISABLED
    btn_cor_fill.config(state=estado)
    lbl_cor_fill.config(foreground='black' if estado == NORMAL else 'gray')

# ── MAIN ───────────────────────────────────────────────────────────────────────
janela = Tk()
janela.title('Linhas & Rabiscos v1.0 ALPHA')
janela.config(bg='#e8e8e8')
janela.resizable(False, False)

main_frame = Frame(janela, bg='#e8e8e8')
main_frame.pack(padx=8, pady=8)

# ── Toolbar (linha superior, itens lado a lado) ────────────────────────────────
toolbar = Frame(main_frame, bg='#e8e8e8', pady=6)
toolbar.grid(row=0, column=0, sticky=EW)

def sep_vertical(col):
    ttk.Separator(toolbar, orient=VERTICAL).grid(
        row=0, column=col, rowspan=2, sticky=NS, padx=10)

# Grupo: Tipo de traço
ttk.Label(toolbar, text='Tipo de traço', background='#e8e8e8',
          font=('Segoe UI', 8, 'bold')).grid(row=0, column=0, sticky=W, padx=(4,4))
tipo_figura_var = StringVar(janela)
option_menu = ttk.OptionMenu(toolbar, tipo_figura_var, 'Linha', 'Linha', 'Rabisco')
option_menu.grid(row=1, column=0, sticky=W, padx=(4,4), pady=(2,0))

sep_vertical(1)

# Grupo: Cor da linha
ttk.Label(toolbar, text='Cor da linha', background='#e8e8e8',
          font=('Segoe UI', 8, 'bold')).grid(row=0, column=2, sticky=W, padx=(4,4))
cor_linha_var = StringVar(janela, value='#000000')
btn_cor_linha = Button(toolbar, bg='#000000', width=4, height=1, relief=RIDGE,
                       command=escolher_cor_linha, cursor='hand2', bd=2)
btn_cor_linha.grid(row=1, column=2, sticky=W, padx=(4,4), pady=(2,0))

sep_vertical(3)

# Grupo: Preenchido
ttk.Label(toolbar, text='Preenchido', background='#e8e8e8',
          font=('Segoe UI', 8, 'bold')).grid(row=0, column=4, sticky=W, padx=(4,4))
preenchido_var = StringVar(janela, value='Não')
frame_radio = Frame(toolbar, bg='#e8e8e8')
frame_radio.grid(row=1, column=4, sticky=W, padx=(4,4), pady=(2,0))
ttk.Radiobutton(frame_radio, text='Sim', variable=preenchido_var, value='Sim',
                command=atualizar_estado_fill).pack(side=LEFT)
ttk.Radiobutton(frame_radio, text='Não', variable=preenchido_var, value='Não',
                command=atualizar_estado_fill).pack(side=LEFT, padx=(8,0))

sep_vertical(5)

# Grupo: Cor de preenchimento
lbl_cor_fill = ttk.Label(toolbar, text='Cor de preenchimento', background='#e8e8e8',
                          font=('Segoe UI', 8, 'bold'), foreground='gray')
lbl_cor_fill.grid(row=0, column=6, sticky=W, padx=(4,4))
cor_fill_var = StringVar(janela, value='#ff0000')
btn_cor_fill = Button(toolbar, bg='#ff0000', width=4, height=1, relief=RIDGE,
                      command=escolher_cor_fill, cursor='hand2', bd=2, state=DISABLED)
btn_cor_fill.grid(row=1, column=6, sticky=W, padx=(4,4), pady=(2,0))

# Separador horizontal entre toolbar e canvas
ttk.Separator(main_frame, orient=HORIZONTAL).grid(row=1, column=0, sticky=EW, pady=6)

# ── Canvas (linha inferior) ────────────────────────────────────────────────────
canvas = Canvas(main_frame, bg='white', width=CANVAS_W, height=CANVAS_H,
                relief=SUNKEN, bd=2, cursor='crosshair')
canvas.grid(row=2, column=0)

# Eventos de mouse
canvas.bind('<ButtonPress-1>', iniciar_figura_nova)
canvas.bind('<B1-Motion>', atualizar_figura_nova)
canvas.bind('<ButtonRelease-1>', incluir_figura_nova)

# Atalhos de teclado
janela.bind('<Control-z>', desfazer)
janela.bind('<Control-Z>', desfazer)
janela.bind('<Control-y>', refazer)
janela.bind('<Control-Y>', refazer)

janela.mainloop()
