from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, flash, g)
from functools import wraps
from models import (init_db, verificar_login, get_usuario,
                    get_empresas_usuario, get_empleados,
                    get_novedades_periodo, guardar_novedad,
                    registrar_log, get_audit_log, get_usuarios_todos,
                    crear_usuario, alta_empleado, get_db)
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "uocra-dev-key-cambiar-en-produccion")

# ── Auth helpers ─────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def estudio_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("rol") != "estudio":
            flash("Acceso restringido al estudio.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

def log(accion, detalle=""):
    if "user_id" in session:
        registrar_log(session["user_id"], accion, detalle,
                      request.remote_addr)

# ── Rutas de autenticación ───────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        email  = request.form.get("email","").strip().lower()
        clave  = request.form.get("clave","").strip()
        usuario = verificar_login(email, clave)
        if usuario:
            session["user_id"] = usuario["id"]
            session["rol"]     = usuario["rol"]
            session["nombre"]  = usuario["nombre"]
            session["email"]   = usuario["email"]
            registrar_log(usuario["id"], "LOGIN", f"email={email}",
                          request.remote_addr)
            return redirect(url_for("dashboard"))
        else:
            error = "Clave incorrecta o usuario no encontrado."
            registrar_log(None, "LOGIN_FALLIDO", f"email={email}",
                          request.remote_addr)
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    log("LOGOUT")
    session.clear()
    return redirect(url_for("login"))

# ── Dashboard ────────────────────────────────────────────────────

@app.route("/")
@login_required
def dashboard():
    empresas = get_empresas_usuario(session["user_id"], session["rol"])
    return render_template("dashboard.html",
                           empresas=empresas,
                           rol=session["rol"],
                           nombre=session["nombre"])

# ── Nómina ───────────────────────────────────────────────────────

@app.route("/nomina/<int:empresa_id>")
@login_required
def nomina(empresa_id):
    db = get_db()
    empresa = db.execute("SELECT * FROM empresas WHERE id=?",
                         (empresa_id,)).fetchone()
    db.close()
    if not empresa:
        flash("Empresa no encontrada.", "error")
        return redirect(url_for("dashboard"))
    empleados = get_empleados(empresa_id)
    log("VER_NOMINA", f"empresa={empresa['nombre']}")
    return render_template("nomina.html",
                           empresa=empresa,
                           empleados=empleados,
                           rol=session["rol"])

@app.route("/empleado/nuevo/<int:empresa_id>", methods=["GET","POST"])
@login_required
def nuevo_empleado(empresa_id):
    db = get_db()
    empresa = db.execute("SELECT * FROM empresas WHERE id=?",
                         (empresa_id,)).fetchone()
    db.close()
    if request.method == "POST":
        datos = {
            "nombre":        request.form["nombre"],
            "cuil":          request.form["cuil"].replace("-","").replace(" ",""),
            "categoria":     request.form["categoria"],
            "jornada":       request.form["jornada"],
            "fecha_ingreso": request.form.get("fecha_ingreso") or None,
            "convenio":      request.form.get("convenio","OBREROS DE LA CONSTRUCCION"),
            "cp":            request.form.get("cp","4000"),
        }
        legajo = alta_empleado(empresa_id, datos)
        log("ALTA_EMPLEADO", f"empresa={empresa_id} nombre={datos['nombre']} legajo={legajo}")
        flash(f"Empleado {datos['nombre']} dado de alta con legajo {legajo}.", "ok")
        return redirect(url_for("nomina", empresa_id=empresa_id))
    return render_template("empleado_form.html", empresa=empresa,
                           rol=session["rol"])

# ── Novedades ────────────────────────────────────────────────────

@app.route("/novedades/<int:empresa_id>")
@login_required
def novedades(empresa_id):
    db = get_db()
    empresa = db.execute("SELECT * FROM empresas WHERE id=?",
                         (empresa_id,)).fetchone()
    db.close()
    mes  = request.args.get("mes",  "")
    anio = request.args.get("anio", "")
    empleados = get_empleados(empresa_id)
    novedades_cargadas = []
    if mes and anio:
        novedades_cargadas = get_novedades_periodo(empresa_id, mes, anio)
    log("VER_NOVEDADES", f"empresa={empresa_id} periodo={mes}/{anio}")
    return render_template("novedades.html",
                           empresa=empresa,
                           empleados=empleados,
                           novedades=novedades_cargadas,
                           mes=mes, anio=anio,
                           rol=session["rol"])

@app.route("/novedades/<int:empresa_id>/guardar", methods=["POST"])
@login_required
def guardar_novedad_route(empresa_id):
    data = request.get_json()
    def flt(v): return float(v) if v not in (None,"") else 0.0

    guardar_novedad(empresa_id, data["empleado_id"],
                    data["mes"], data["anio"],
                    {
                        "estado":    data.get("estado","A"),
                        "fecha_ini": data.get("fecha_ini"),
                        "fecha_fin": data.get("fecha_fin"),
                        "hs1":  flt(data.get("hs1")),
                        "inas1":flt(data.get("inas1")),
                        "enf1": flt(data.get("enf1")),
                        "fer1": flt(data.get("fer1")),
                        "vac1": flt(data.get("vac1")),
                        "ext1": flt(data.get("ext1")),
                        "hs2":  flt(data.get("hs2")),
                        "inas2":flt(data.get("inas2")),
                        "enf2": flt(data.get("enf2")),
                        "fer2": flt(data.get("fer2")),
                        "vac2": flt(data.get("vac2")),
                        "ext2": flt(data.get("ext2")),
                        "obs":  data.get("obs",""),
                    },
                    session["user_id"])
    log("GUARDAR_NOVEDAD",
        f"empresa={empresa_id} empleado={data['empleado_id']} periodo={data['mes']}/{data['anio']}")
    return jsonify({"ok": True, "msg": "Guardado correctamente"})

@app.route("/novedades/<int:empresa_id>/empleado/<int:empleado_id>")
@login_required
def novedad_empleado(empresa_id, empleado_id):
    mes  = request.args.get("mes","")
    anio = request.args.get("anio","")
    db = get_db()
    empresa  = db.execute("SELECT * FROM empresas WHERE id=?", (empresa_id,)).fetchone()
    empleado = db.execute("SELECT * FROM empleados WHERE id=?", (empleado_id,)).fetchone()
    nov = None
    if mes and anio:
        nov = db.execute("""
            SELECT * FROM novedades
            WHERE empresa_id=? AND empleado_id=? AND periodo_mes=? AND periodo_anio=?
        """, (empresa_id, empleado_id, mes, anio)).fetchone()
    db.close()
    return render_template("novedad_form.html",
                           empresa=empresa,
                           empleado=empleado,
                           novedad=nov,
                           mes=mes, anio=anio,
                           rol=session["rol"])

# ── Informe de control ───────────────────────────────────────────

@app.route("/informe/<int:empresa_id>")
@login_required
def informe(empresa_id):
    mes  = request.args.get("mes","")
    anio = request.args.get("anio","")
    db = get_db()
    empresa = db.execute("SELECT * FROM empresas WHERE id=?", (empresa_id,)).fetchone()
    db.close()
    novedades_data = []
    if mes and anio:
        novedades_data = get_novedades_periodo(empresa_id, mes, anio)
    log("VER_INFORME", f"empresa={empresa_id} periodo={mes}/{anio}")
    return render_template("informe.html",
                           empresa=empresa,
                           novedades=novedades_data,
                           mes=mes, anio=anio,
                           rol=session["rol"])

# ── Admin — solo estudio ─────────────────────────────────────────

@app.route("/admin/log")
@estudio_required
def admin_log():
    logs = get_audit_log(300)
    return render_template("admin/log.html", logs=logs, rol=session["rol"])

@app.route("/admin/usuarios")
@estudio_required
def admin_usuarios():
    db = get_db()
    usuarios = get_usuarios_todos()
    empresas = db.execute("SELECT * FROM empresas WHERE activa=1").fetchall()
    db.close()
    return render_template("admin/usuarios.html",
                           usuarios=usuarios, empresas=empresas,
                           rol=session["rol"])

@app.route("/admin/usuarios/nuevo", methods=["POST"])
@estudio_required
def admin_nuevo_usuario():
    email    = request.form["email"].strip().lower()
    password = request.form["password"].strip()
    nombre   = request.form["nombre"].strip()
    rol      = request.form["rol"]
    empresas = request.form.getlist("empresas")
    try:
        uid = crear_usuario(email, password, nombre, rol,
                            [int(e) for e in empresas])
        log("CREAR_USUARIO", f"email={email} rol={rol}")
        flash(f"Usuario {nombre} creado.", "ok")
    except Exception as ex:
        flash(f"Error: {ex}", "error")
    return redirect(url_for("admin_usuarios"))

@app.route("/admin/empresas/nueva", methods=["POST"])
@estudio_required
def admin_nueva_empresa():
    nombre = request.form["nombre"].strip()
    cuit   = request.form.get("cuit","").strip()
    db = get_db()
    db.execute("INSERT INTO empresas (nombre, cuit) VALUES (?,?)", (nombre, cuit))
    db.commit()
    db.close()
    log("CREAR_EMPRESA", f"nombre={nombre}")
    flash(f"Empresa {nombre} creada.", "ok")
    return redirect(url_for("dashboard"))

# ── Init y run ───────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)


# ══════════════════════════════════════════════════════════════════
# MÓDULO: Confirmar período + Documentación + Config empresa/mail
# ══════════════════════════════════════════════════════════════════

from mail import (mail_periodo_confirmado, mail_documento_subido,
                  mail_documento_revisado)
from models import (save_config_empresa, save_config_mail, get_config_mail,
                    confirmar_periodo, periodo_ya_confirmado,
                    subir_documento, get_documentos_empleado, get_documento,
                    revisar_documento, get_documentos_pendientes_empresa,
                    get_resumen_docs_empleado, DOCS_POR_ESTADO, DOC_LABELS,
                    ESTADO_EMPL_LABEL)
from flask import send_file
import io

# ── Confirmar período ─────────────────────────────────────────────

@app.route("/novedades/<int:empresa_id>/confirmar", methods=["POST"])
@login_required
def confirmar_periodo_route(empresa_id):
    mes  = request.form.get("mes","")
    anio = request.form.get("anio","")
    if not mes or not anio:
        return jsonify({"ok":False,"msg":"Período inválido"})

    if periodo_ya_confirmado(empresa_id, mes, anio):
        return jsonify({"ok":False,"msg":"Este período ya fue confirmado anteriormente."})

    novedades_data = get_novedades_periodo(empresa_id, mes, anio)
    if not novedades_data:
        return jsonify({"ok":False,"msg":"No hay novedades cargadas para confirmar."})

    confirmar_periodo(empresa_id, mes, anio)
    log("CONFIRMAR_PERIODO", f"empresa={empresa_id} periodo={mes}/{anio}")

    # Mail silencioso al estudio
    db = get_db()
    empresa = db.execute("SELECT * FROM empresas WHERE id=?",(empresa_id,)).fetchone()
    db.close()
    try:
        mail_periodo_confirmado(dict(empresa), mes, anio,
                                [dict(n) for n in novedades_data],
                                empresa["mail"])
    except Exception as e:
        print(f"[MAIL] Error: {e}")

    return jsonify({"ok":True,"msg":f"Período {mes}/{anio} confirmado. Mail enviado al estudio."})

# ── Config empresa ────────────────────────────────────────────────

@app.route("/empresa/<int:empresa_id>/config", methods=["GET","POST"])
@login_required
def config_empresa(empresa_id):
    db = get_db()
    empresa = db.execute("SELECT * FROM empresas WHERE id=?",(empresa_id,)).fetchone()
    db.close()
    if request.method == "POST":
        save_config_empresa(empresa_id, {
            "nombre":    request.form.get("nombre",""),
            "cuit":      request.form.get("cuit",""),
            "domicilio": request.form.get("domicilio",""),
            "actividad": request.form.get("actividad",""),
            "mail":      request.form.get("mail",""),
            "cbu":       request.form.get("cbu",""),
        })
        log("CONFIG_EMPRESA", f"empresa={empresa_id}")
        flash("Configuración guardada.", "ok")
        return redirect(url_for("config_empresa", empresa_id=empresa_id))
    return render_template("config_empresa.html", empresa=empresa, rol=session["rol"])

# ── Config mail (solo estudio) ────────────────────────────────────

@app.route("/admin/mail", methods=["GET","POST"])
@estudio_required
def admin_mail():
    cfg = get_config_mail()
    if request.method == "POST":
        save_config_mail({
            "smtp_host":     request.form.get("smtp_host","smtp.gmail.com"),
            "smtp_port":     int(request.form.get("smtp_port",587)),
            "smtp_user":     request.form.get("smtp_user",""),
            "smtp_password": request.form.get("smtp_password",""),
            "mail_estudio_1":request.form.get("mail_estudio_1",""),
            "mail_estudio_2":request.form.get("mail_estudio_2",""),
        })
        log("CONFIG_MAIL", "actualizada")
        flash("Configuración de mail guardada.", "ok")
        return redirect(url_for("admin_mail"))
    return render_template("admin/config_mail.html", cfg=cfg, rol=session["rol"])

# ── Documentos ────────────────────────────────────────────────────

@app.route("/docs/<int:empresa_id>/empleado/<int:empleado_id>")
@login_required
def docs_empleado(empresa_id, empleado_id):
    db = get_db()
    empresa  = db.execute("SELECT * FROM empresas WHERE id=?",(empresa_id,)).fetchone()
    empleado = db.execute("SELECT * FROM empleados WHERE id=?",(empleado_id,)).fetchone()
    db.close()
    docs = get_documentos_empleado(empresa_id, empleado_id)
    estado_empl = empleado["estado"]
    requeridos  = DOCS_POR_ESTADO.get(estado_empl, [])
    subidos, pendientes = get_resumen_docs_empleado(empresa_id, empleado_id, estado_empl)
    return render_template("docs_empleado.html",
        empresa=empresa, empleado=empleado, docs=docs,
        requeridos=requeridos, pendientes=pendientes,
        DOC_LABELS=DOC_LABELS, ESTADO_EMPL_LABEL=ESTADO_EMPL_LABEL,
        rol=session["rol"])

@app.route("/docs/<int:empresa_id>/empleado/<int:empleado_id>/subir", methods=["POST"])
@login_required
def subir_doc(empresa_id, empleado_id):
    tipo_doc    = request.form.get("tipo_doc","")
    estado_empl = request.form.get("estado_empl","")
    archivo     = request.files.get("archivo")
    if not archivo or not tipo_doc:
        flash("Datos incompletos.", "error")
        return redirect(request.referrer)

    datos_bin  = archivo.read()
    mime_type  = archivo.content_type or "application/octet-stream"
    nombre_arch = archivo.filename
    origen = session["rol"]  # 'estudio' o 'cliente'

    doc_id = subir_documento(empresa_id, empleado_id, tipo_doc, estado_empl,
                              nombre_arch, datos_bin, mime_type,
                              origen, session["user_id"])
    log("SUBIR_DOC", f"empresa={empresa_id} emp={empleado_id} tipo={tipo_doc} origen={origen}")

    # Mail automático
    db = get_db()
    empresa  = db.execute("SELECT * FROM empresas WHERE id=?",(empresa_id,)).fetchone()
    empleado = db.execute("SELECT * FROM empleados WHERE id=?",(empleado_id,)).fetchone()
    db.close()
    cfg = get_config_mail()
    doc_label = DOC_LABELS.get(tipo_doc, tipo_doc)

    try:
        if origen == "cliente":
            # Notificar al estudio
            destinos = [x for x in [cfg["mail_estudio_1"], cfg["mail_estudio_2"]] if x]
        else:
            # Notificar al cliente
            destinos = [empresa["mail"]] if empresa["mail"] else []
        if destinos:
            mail_documento_subido(dict(empresa), dict(empleado),
                                  tipo_doc, doc_label, estado_empl,
                                  origen, destinos)
    except Exception as e:
        print(f"[MAIL] Error: {e}")

    flash(f"Documento '{doc_label}' subido correctamente.", "ok")
    return redirect(url_for("docs_empleado", empresa_id=empresa_id, empleado_id=empleado_id))

@app.route("/docs/ver/<int:doc_id>")
@login_required
def ver_doc(doc_id):
    doc = get_documento(doc_id)
    if not doc:
        flash("Documento no encontrado.", "error")
        return redirect(url_for("dashboard"))
    return send_file(
        io.BytesIO(doc["datos"]),
        mimetype=doc["mime_type"],
        as_attachment=False,
        download_name=doc["nombre_arch"]
    )

@app.route("/docs/descargar/<int:doc_id>")
@login_required
def descargar_doc(doc_id):
    doc = get_documento(doc_id)
    if not doc:
        flash("Documento no encontrado.", "error")
        return redirect(url_for("dashboard"))
    return send_file(
        io.BytesIO(doc["datos"]),
        mimetype=doc["mime_type"],
        as_attachment=True,
        download_name=doc["nombre_arch"]
    )

@app.route("/docs/revisar/<int:doc_id>", methods=["POST"])
@estudio_required
def revisar_doc(doc_id):
    estado     = request.form.get("estado","")
    comentario = request.form.get("comentario","")
    doc = get_documento(doc_id)
    if not doc:
        return jsonify({"ok":False,"msg":"No encontrado"})

    revisar_documento(doc_id, estado, comentario, session["user_id"])
    log("REVISAR_DOC", f"doc={doc_id} estado={estado}")

    # Mail al cliente si fue rechazado
    if doc["origen"] == "cliente" and estado in ("aprobado","rechazado"):
        db = get_db()
        empresa  = db.execute("SELECT * FROM empresas WHERE id=?",(doc["empresa_id"],)).fetchone()
        empleado = db.execute("SELECT * FROM empleados WHERE id=?",(doc["empleado_id"],)).fetchone()
        db.close()
        if empresa["mail"]:
            try:
                mail_documento_revisado(dict(empresa), dict(empleado),
                    doc["tipo_doc"], DOC_LABELS.get(doc["tipo_doc"], doc["tipo_doc"]),
                    estado, comentario, [empresa["mail"]])
            except Exception as e:
                print(f"[MAIL] Error: {e}")

    return jsonify({"ok":True,"msg":f"Documento marcado como {estado}."})

@app.route("/docs/<int:empresa_id>/pendientes")
@estudio_required
def docs_pendientes(empresa_id):
    db = get_db()
    empresa = db.execute("SELECT * FROM empresas WHERE id=?",(empresa_id,)).fetchone()
    db.close()
    docs = get_documentos_pendientes_empresa(empresa_id)
    return render_template("docs_pendientes.html",
        empresa=empresa, docs=docs,
        DOC_LABELS=DOC_LABELS, ESTADO_EMPL_LABEL=ESTADO_EMPL_LABEL,
        rol=session["rol"])
