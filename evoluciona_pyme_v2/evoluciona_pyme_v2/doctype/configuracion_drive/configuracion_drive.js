frappe.ui.form.on("Configuracion_Drive", {
    refresh(frm) {
        // Show the redirect URI
        frappe.call({
            method: "evoluciona_pyme_v2.evoluciona_pyme_v2.drive.get_redirect_uri_info",
            callback(r) {
                if (r.message) {
                    frm.set_value("oauth_redirect_uri", r.message);
                }
            }
        });

        // URL de autorización dinámica
        frappe.call({
            method: "evoluciona_pyme_v2.evoluciona_pyme_v2.drive.get_redirect_uri_info",
            callback(r) {
                const redirect_uri = r.message || "";
                const client_id = frm.doc.oauth_client_id || "TU_CLIENT_ID";
                const auth_url = client_id !== "TU_CLIENT_ID"
                    ? `https://accounts.google.com/o/oauth2/auth?client_id=${client_id}&redirect_uri=${encodeURIComponent(redirect_uri)}&response_type=code&scope=https://www.googleapis.com/auth/drive&access_type=offline&prompt=consent`
                    : null;

                const url_html = auth_url
                    ? `<div style="background:#e8f4fd; border:1px solid #bee5eb; border-radius:8px; padding:12px; margin-bottom:8px;">
                        <b>🔗 URL de Autorización OAuth2</b><br>
                        <small style="color:#555;">Abre esta URL en el navegador para autorizar.</small><br><br>
                        <code style="background:#fff; padding:8px; border-radius:4px; display:block; font-size:11px; word-break:break-all; border:1px solid #ccc;">${auth_url}</code>
                        <br><button class="btn btn-xs btn-primary" onclick="window.open('${auth_url}','_blank')">Abrir URL</button>
                       </div>`
                    : `<div style="background:#fff3cd; border:1px solid #ffc107; border-radius:8px; padding:12px;">
                        ⚠️ Ingresa el <b>OAuth Client ID</b> para ver la URL de autorización.
                       </div>`;

                frm.get_field("html_url_autorizacion").$wrapper.html(url_html);
            }
        });

        // OAuth status indicator
        if (frm.doc.oauth_autorizado) {
            frm.dashboard.set_headline_alert(
                '<span class="indicator green"></span> OAuth2 autorizado — los archivos se subirán con la cuenta del usuario.',
                "green"
            );
        } else {
            frm.dashboard.set_headline_alert(
                '<span class="indicator orange"></span> OAuth2 no autorizado — se usará Service Account (sin cuota para archivos).',
                "orange"
            );
        }

        // Main OAuth button using OAuth Playground (works with IP servers)
        frm.add_custom_button(__("Autorizar con OAuth Playground"), function () {
            if (!frm.doc.oauth_client_id) {
                frappe.msgprint(__("Ingresa el OAuth Client ID antes de autorizar."));
                return;
            }

            frm.save().then(() => {
                frappe.call({
                    method: "evoluciona_pyme_v2.evoluciona_pyme_v2.drive.iniciar_oauth_drive",
                    args: { usar_playground: true },
                    callback(r) {
                        if (!r.message) return;

                        const auth_url = r.message;

                        const dialog = new frappe.ui.Dialog({
                            title: "Autorizar Google Drive con OAuth Playground",
                            fields: [
                                {
                                    fieldtype: "HTML",
                                    options: `
                                        <div class="frappe-card" style="padding:16px; margin-bottom:12px;">
                                            <p><b>Paso 1:</b> En Google Cloud Console, agrega esta URI de redirección:</p>
                                            <code style="background:#f4f5f6; padding:6px 10px; border-radius:4px; display:block; margin:8px 0; user-select:all;">
                                                https://developers.google.com/oauthplayground
                                            </code>
                                            <p style="margin-top:12px;"><b>Paso 2:</b> Abre OAuth Playground con el botón de abajo.</p>
                                            <p><b>Paso 3:</b> En OAuth Playground, haz clic en el ícono ⚙️ (Configuración) arriba a la derecha, activa <b>"Use your own OAuth credentials"</b> e ingresa tu Client ID y Client Secret.</p>
                                            <p><b>Paso 4:</b> En el campo de scopes, pega:</p>
                                            <code style="background:#f4f5f6; padding:6px 10px; border-radius:4px; display:block; margin:8px 0; user-select:all;">
                                                https://www.googleapis.com/auth/drive
                                            </code>
                                            <p><b>Paso 5:</b> Autoriza → Exchange code for tokens → copia el <b>Refresh Token</b>.</p>
                                            <p><b>Paso 6:</b> Pega el Refresh Token en el campo de abajo y confirma.</p>
                                        </div>
                                    `
                                },
                                {
                                    fieldtype: "Button",
                                    label: "Abrir OAuth Playground",
                                    click() {
                                        window.open(auth_url, "_blank");
                                    }
                                },
                                {
                                    fieldname: "refresh_token",
                                    fieldtype: "Password",
                                    label: "Refresh Token (pegar aquí)",
                                    reqd: 1
                                }
                            ],
                            primary_action_label: "Guardar Token",
                            primary_action(values) {
                                frappe.call({
                                    method: "evoluciona_pyme_v2.evoluciona_pyme_v2.drive.guardar_refresh_token_manual",
                                    args: { refresh_token: values.refresh_token },
                                    callback(r) {
                                        if (r.message && r.message.status === "ok") {
                                            dialog.hide();
                                            frm.reload_doc();
                                            frappe.show_alert({ message: "¡OAuth2 autorizado correctamente!", indicator: "green" });
                                        }
                                    }
                                });
                            }
                        });
                        dialog.show();
                    }
                });
            });
        }, __("OAuth2"));

        // Revoke button
        if (frm.doc.oauth_autorizado) {
            frm.add_custom_button(__("Revocar Autorización"), function () {
                frappe.confirm(
                    "¿Seguro que deseas revocar la autorización OAuth2?",
                    () => {
                        frappe.db.set_value("Configuracion_Drive", "Configuracion_Drive", {
                            oauth_refresh_token: "",
                            oauth_autorizado: 0
                        }).then(() => {
                            frm.reload_doc();
                            frappe.show_alert({ message: "Autorización revocada.", indicator: "orange" });
                        });
                    }
                );
            }, __("OAuth2"));
        }
    }
});
