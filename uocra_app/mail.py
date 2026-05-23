import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from models import get_config_mail

def _get_cfg():
    cfg = get_config_mail()
    if not cfg or not cfg["smtp_user"]:
        return None
    return dict(cfg)

def enviar_mail(destinatarios, asunto, html, adjuntos=None):
    """
    destinatarios: list de emails
    adjuntos: list de dicts {nombre, datos (bytes), mime_type}
    """
    cfg = _get_cfg()
    if not cfg:
        print("[MAIL] Sin configuración SMTP — mail no enviado.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = cfg["smtp_user"]
        msg["To"]      = ", ".join(destinatarios)
        msg["Subject"] = asunto
        msg.attach(MIMEText(html, "html", "utf-8"))

        if adjuntos:
            for adj in adjuntos:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(adj["datos"])
                encoders.encode_base64(part)
                part.add_header("Content-Disposition",
                                f'attachment; filename="{adj["nombre"]}"')
                msg.attach(part)

        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as s:
            s.ehlo()
            s.starttls()
            s.login(cfg["smtp_user"], cfg["smtp_password"])
            s.sendmail(cfg["smtp_user"], destinatarios, msg.as_string())
        return True
    except Exception as e:
        print(f"[MAIL] Error: {e}")
        return False

# ── Templates de mail ─────────────────────────────────────────────

def _base_html(titulo, contenido, footer="CL Gestión Laboral — Sistema UOCRA"):
    return f"""
<div style="font-family:Arial,sans-serif;font-size:13px;max-width:600px;margin:0 auto">
  <div style="background:#1F3864;color:#fff;padding:16px 22px;border-radius:8px 8px 0 0">
    <strong style="font-size:15px">&#9679; {titulo}</strong>
  </div>
  <div style="background:#fff;border:1px solid #ddd;border-radius:0 0 8px 8px;padding:20px 22px">
    {contenido}
  </div>
  <div style="text-align:center;font-size:10px;color:#9c9890;margin-top:8px">{footer}</div>
</div>"""

def mail_periodo_confirmado(empresa, mes, anio, novedades, mail_empresa):
    """Mail al estudio cuando el cliente confirma el período."""
    cfg = get_config_mail()
    destinatarios = []
    if cfg:
        if cfg["mail_estudio_1"]: destinatarios.append(cfg["mail_estudio_1"])
        if cfg["mail_estudio_2"]: destinatarios.append(cfg["mail_estudio_2"])

    meses = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
             'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    mes_txt = meses[int(mes)] if mes.isdigit() else mes
    per = f"{mes}/{anio}"

    filas = "".join(
        f"<tr><td style='padding:5px 8px;border-bottom:1px solid #eee'>{n['legajo']}</td>"
        f"<td style='padding:5px 8px;border-bottom:1px solid #eee;font-weight:500'>{n['emp_nombre']}</td>"
        f"<td style='padding:5px 8px;border-bottom:1px solid #eee;text-align:center'><span style='background:#e3f2fd;color:#1565c0;padding:1px 6px;border-radius:3px;font-size:11px'>{n['estado']}</span></td>"
        f"<td style='padding:5px 8px;border-bottom:1px solid #eee;text-align:center;font-family:monospace'>{(n['hs1'] or 0)+(n['hs2'] or 0)}</td>"
        f"</tr>"
        for n in novedades
    )

    contenido = f"""
    <p><strong>Empresa:</strong> {empresa['nombre']}</p>
    <p><strong>Período:</strong> {mes_txt} {anio}</p>
    <p style="color:#2e7d32;font-weight:bold;margin:10px 0">
      ✓ Período confirmado por el cliente
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:12px 0">
    <h3 style="color:#1F3864;font-size:13px;margin-bottom:8px">
      Novedades cargadas ({len(novedades)})
    </h3>
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead>
        <tr style="background:#f5f4f0">
          <th style="padding:5px 8px;text-align:left">Leg.</th>
          <th style="padding:5px 8px;text-align:left">Empleado</th>
          <th style="padding:5px 8px;text-align:center">Estado</th>
          <th style="padding:5px 8px;text-align:center">Hs totales</th>
        </tr>
      </thead>
      <tbody>{filas}</tbody>
    </table>
    <hr style="border:none;border-top:1px solid #eee;margin:12px 0">
    <p style="font-size:10px;color:#9c9890">Generado automáticamente — sin responder</p>
    """

    asunto = f"UOCRA — {empresa['nombre']} — Período {per} confirmado ✓"
    html = _base_html(f"Período {per} confirmado — {empresa['nombre']}", contenido)
    return enviar_mail(destinatarios, asunto, html)


def mail_documento_subido(empresa, empleado, tipo_doc, doc_label,
                          estado_empl, origen, mail_destinos):
    """
    Notifica que se subió un documento.
    origen='cliente' → notifica al estudio
    origen='estudio' → notifica al cliente (mail de empresa)
    """
    estado_label = {"I":"Incorporación","E":"Enfermedad","V":"Vacaciones",
                    "ART":"ART","B":"Baja"}.get(estado_empl, estado_empl)

    if origen == "cliente":
        titulo_accion = "El cliente subió documentación"
        nota = "Ingresá al sistema para revisar y aprobar."
        color = "#1565c0"
    else:
        titulo_accion = "El estudio subió documentación para tu empresa"
        nota = "Ingresá al sistema para verificar."
        color = "#2e7d32"

    contenido = f"""
    <p><strong>Empresa:</strong> {empresa['nombre']}</p>
    <p><strong>Empleado:</strong> {empleado['legajo']} — {empleado['nombre']}</p>
    <p><strong>Motivo:</strong> {estado_label}</p>
    <p><strong>Documento:</strong>
      <span style="background:#e3f2fd;color:{color};padding:2px 8px;border-radius:3px;font-weight:bold">
        {doc_label}
      </span>
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:12px 0">
    <p style="color:{color};font-weight:bold">{nota}</p>
    <p style="font-size:10px;color:#9c9890;margin-top:12px">Generado automáticamente — sin responder</p>
    """
    asunto = f"UOCRA — {empresa['nombre']} — Nueva documentación: {doc_label}"
    html = _base_html(titulo_accion, contenido)
    return enviar_mail(mail_destinos, asunto, html)


def mail_documento_revisado(empresa, empleado, tipo_doc, doc_label,
                             estado_doc, comentario, mail_destinos):
    """Notifica al cliente cuando el estudio aprueba o rechaza un documento."""
    ok = estado_doc == "aprobado"
    color = "#2e7d32" if ok else "#b71c1c"
    icono = "✓" if ok else "✗"
    contenido = f"""
    <p><strong>Empresa:</strong> {empresa['nombre']}</p>
    <p><strong>Empleado:</strong> {empleado['legajo']} — {empleado['nombre']}</p>
    <p><strong>Documento:</strong> {doc_label}</p>
    <p style="color:{color};font-weight:bold;font-size:14px;margin:12px 0">
      {icono} {estado_doc.upper()}
    </p>
    {'<p><strong>Comentario:</strong> '+comentario+'</p>' if comentario else ''}
    {'<p style="color:#b71c1c">Por favor corregí y volvé a subir el documento.</p>' if not ok else ''}
    <p style="font-size:10px;color:#9c9890;margin-top:12px">Generado automáticamente — sin responder</p>
    """
    asunto = f"UOCRA — {empresa['nombre']} — Documento {estado_doc}: {doc_label}"
    html = _base_html(f"Revisión de documentación — {empresa['nombre']}", contenido)
    return enviar_mail(mail_destinos, asunto, html)
