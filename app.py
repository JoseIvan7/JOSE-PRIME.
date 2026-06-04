import streamlit as st
import pandas as pd
import time
from datetime import datetime
import json
import os

from storage import cargar_datos_desde_sheets, guardar_datos_en_sheets
st.set_page_config(
    page_title="JOSE PRIME",
    page_icon="💪",
    layout="wide"
)

DATA_FILE = "gym_data.json"


def datos_iniciales():
    return {
        "dias": {
            "lunes": {
                "nombre": "Lunes",
                "musculos": "Pecho · Tríceps · Hombro",
                "ultima_rutina": []
            },
            "martes": {
                "nombre": "Martes",
                "musculos": "Espalda · Bíceps · Hombro post",
                "ultima_rutina": []
            },
            "miercoles": {
                "nombre": "Miércoles",
                "musculos": "Pierna · Glúteo · Gemelo",
                "ultima_rutina": []
            },
            "jueves": {
                "nombre": "Jueves",
                "musculos": "Hombro · Abdomen · Brazos",
                "ultima_rutina": []
            },
            "viernes": {
                "nombre": "Viernes",
                "musculos": "Full body · Core · Cardio",
                "ultima_rutina": []
            }
        },
        "ejercicios": {},
        "historial": [],
        "sesiones": []
    }


def cargar_datos():
    return cargar_datos_desde_sheets()


def guardar_datos(datos):
    guardar_datos_en_sheets(datos)


def init_state():
    valores = {
        "pantalla": "home",
        "dia_actual": None,
        "seleccion_sesion": [],
        "completados": [],
        "ejercicio_actual": None,
        "serie_actual": 1,
        "orden_real": [],
        "inicio_sesion": None
    }

    for k, v in valores.items():
        if k not in st.session_state:
            st.session_state[k] = v


def cambiar_pantalla(nombre):
    st.session_state.pantalla = nombre
    st.rerun()


def formato_ejercicio(e):
    return f"{e['peso']} · {e['series']}x{e['reps']}"


def ejercicios_del_dia(datos, dia_id):
    return {
        k: v for k, v in datos["ejercicios"].items()
        if v["dia"] == dia_id
    }


def mostrar_home(datos):
    st.title("💪 JOSE PRIME")
    st.caption("Rutina semanal · Lunes a viernes")

    dias_orden = ["lunes", "martes", "miercoles", "jueves", "viernes"]
    columnas = st.columns(5)

    for col, dia_id in zip(columnas, dias_orden):
        dia = datos["dias"][dia_id]

        with col:
            st.markdown(f"### {dia['nombre'].upper()}")
            st.caption(dia["musculos"])
            st.divider()

            st.write("**Última rutina**")

            for ej_id in dia["ultima_rutina"]:
                if ej_id in datos["ejercicios"]:
                    e = datos["ejercicios"][ej_id]
                    st.write(f"• {e['nombre']}")
                    st.caption(formato_ejercicio(e))

            if st.button("Abrir día", key=f"abrir_{dia_id}", use_container_width=True):
                st.session_state.dia_actual = dia_id
                cambiar_pantalla("dia")

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        if st.button("📜 Ver sesiones", use_container_width=True):
            cambiar_pantalla("sesiones")

    with c2:
        if st.button("🏋️ Gestionar ejercicios", use_container_width=True):
            cambiar_pantalla("gestionar_ejercicios")


def mostrar_bloque_ejercicios(datos, lista):
    if not lista:
        st.info("No hay ejercicios aquí todavía.")
        return

    for ej_id, e in lista:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1, 1])

            with c1:
                st.write(f"**{e['nombre']}**")
                st.caption(f"{e['musculo']} · {formato_ejercicio(e)}")

            with c2:
                if st.button("Editar", key=f"editar_{ej_id}"):
                    st.session_state.ejercicio_actual = ej_id
                    cambiar_pantalla("editar")

            with c3:
                if st.button("H", key=f"hist_{ej_id}"):
                    st.session_state.ejercicio_actual = ej_id
                    cambiar_pantalla("historial")


def mostrar_dia(datos):
    dia_id = st.session_state.dia_actual
    dia = datos["dias"][dia_id]

    if st.button("← Volver"):
        cambiar_pantalla("home")

    st.title(dia["nombre"])
    st.caption(dia["musculos"])

    todos = ejercicios_del_dia(datos, dia_id)
    ultimos_ids = dia["ultima_rutina"]

    ultimos = [(k, todos[k]) for k in ultimos_ids if k in todos]
    otros = [(k, v) for k, v in todos.items() if k not in ultimos_ids]

    st.subheader("Últimos usados")
    mostrar_bloque_ejercicios(datos, ultimos)

    st.subheader("Otros disponibles")
    mostrar_bloque_ejercicios(datos, otros)

    st.divider()
    st.subheader("Iniciar rutina")

    opciones = {}
    defaults = []

    for ej_id, e in ultimos + otros:
        label = f"{e['nombre']} — {formato_ejercicio(e)}"
        opciones[label] = ej_id
        if ej_id in ultimos_ids:
            defaults.append(label)

    seleccion = st.multiselect(
        "Selecciona ejercicios para hoy",
        list(opciones.keys()),
        default=defaults
    )

    if st.button("INICIAR RUTINA", type="primary", use_container_width=True):
        if not seleccion:
            st.warning("Selecciona al menos un ejercicio.")
            return

        st.session_state.seleccion_sesion = [opciones[s] for s in seleccion]
        st.session_state.completados = []
        st.session_state.ejercicio_actual = None
        st.session_state.serie_actual = 1
        st.session_state.orden_real = []
        st.session_state.inicio_sesion = datetime.now().isoformat(timespec="seconds")
        cambiar_pantalla("sesion")


def mostrar_sesion(datos):
    st.title("Sesión activa")

    pendientes = [
        ej_id for ej_id in st.session_state.seleccion_sesion
        if ej_id not in st.session_state.completados
    ]

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("✅ Completados")
        if st.session_state.completados:
            for ej_id in st.session_state.completados:
                st.write(f"✅ {datos['ejercicios'][ej_id]['nombre']}")
        else:
            st.caption("Todavía ninguno.")

    with c2:
        st.subheader("○ Pendientes")
        if pendientes:
            for ej_id in pendientes:
                st.write(f"○ {datos['ejercicios'][ej_id]['nombre']}")
        else:
            st.success("Todos completados.")

    st.divider()

    if not pendientes:
        st.success("Has completado todos los ejercicios seleccionados.")

        if st.button("FIN DE SESIÓN", type="primary", use_container_width=True):
            finalizar_sesion(datos)
            cambiar_pantalla("home")

        return

    st.subheader("Elige el siguiente ejercicio")

    for ej_id in pendientes:
        e = datos["ejercicios"][ej_id]
        if st.button(f"{e['nombre']} — {formato_ejercicio(e)}", key=f"elegir_{ej_id}", use_container_width=True):
            st.session_state.ejercicio_actual = ej_id
            st.session_state.serie_actual = 1
            cambiar_pantalla("ejercicio_activo")


def mostrar_ejercicio_activo(datos):
    ej_id = st.session_state.ejercicio_actual
    e = datos["ejercicios"][ej_id]

    st.title(e["nombre"])
    st.caption(f"{e['musculo']} · {formato_ejercicio(e)}")

    st.metric("Serie actual", f"{st.session_state.serie_actual} de {e['series']}")

    if st.button("COMPLETAR SERIE", type="primary", use_container_width=True):
        if st.session_state.serie_actual < e["series"]:
            cambiar_pantalla("descanso_serie")
        else:
            cambiar_pantalla("resumen_ejercicio")

    if st.button("Cancelar y volver a sesión"):
        cambiar_pantalla("sesion")


def contador(segundos, titulo):
    st.title(titulo)
    placeholder = st.empty()

    if st.button("Saltar descanso"):
        return

    for restante in range(segundos, 0, -1):
        minutos = restante // 60
        seg = restante % 60
        placeholder.metric("Tiempo restante", f"{minutos:02d}:{seg:02d}")
        time.sleep(1)


def mostrar_descanso_serie():
    contador(90, "Descanso entre series")
    st.session_state.serie_actual += 1
    cambiar_pantalla("ejercicio_activo")


def mostrar_resumen_ejercicio(datos):
    ej_id = st.session_state.ejercicio_actual
    e = datos["ejercicios"][ej_id]

    st.title(f"{e['nombre']} completado")
    st.caption("Modifica solo si has mejorado o empeorado.")

    with st.form("resumen_ejercicio"):
        nuevo_peso = st.text_input("Peso", value=e["peso"])
        nuevas_series = st.number_input("Series", min_value=1, max_value=10, value=int(e["series"]))
        nuevas_reps = st.number_input("Reps", min_value=1, max_value=100, value=int(e["reps"]))
        nota = st.text_area("Nota opcional")
        guardar = st.form_submit_button("Guardar ejercicio")

    if guardar:
        old = e.copy()

        cambio = (
            old["peso"] != nuevo_peso
            or old["series"] != int(nuevas_series)
            or old["reps"] != int(nuevas_reps)
        )

        if cambio:
            datos["historial"].append({
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "ejercicio_id": ej_id,
                "ejercicio": e["nombre"],
                "antes": formato_ejercicio(old),
                "despues": f"{nuevo_peso} · {int(nuevas_series)}x{int(nuevas_reps)}",
                "nota": nota
            })

            datos["ejercicios"][ej_id]["peso"] = nuevo_peso
            datos["ejercicios"][ej_id]["series"] = int(nuevas_series)
            datos["ejercicios"][ej_id]["reps"] = int(nuevas_reps)

        st.session_state.completados.append(ej_id)
        st.session_state.orden_real.append(ej_id)

        guardar_datos(datos)

        pendientes = [
            x for x in st.session_state.seleccion_sesion
            if x not in st.session_state.completados
        ]

        if pendientes:
            cambiar_pantalla("descanso_ejercicio")
        else:
            cambiar_pantalla("sesion")


def mostrar_descanso_ejercicio():
    contador(180, "Descanso entre ejercicios")
    cambiar_pantalla("sesion")


def finalizar_sesion(datos):
    dia_id = st.session_state.dia_actual
    inicio = st.session_state.inicio_sesion
    fin = datetime.now().isoformat(timespec="seconds")

    if inicio:
        inicio_dt = datetime.fromisoformat(inicio)
        fin_dt = datetime.fromisoformat(fin)
        duracion = int((fin_dt - inicio_dt).total_seconds() // 60)
    else:
        duracion = 0

    sesion = {
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "dia": datos["dias"][dia_id]["nombre"],
        "dia_id": dia_id,
        "inicio": inicio,
        "fin": fin,
        "duracion_min": duracion,
        "ejercicios": [
            datos["ejercicios"][ej_id]["nombre"]
            for ej_id in st.session_state.orden_real
        ],
        "ejercicio_ids": st.session_state.orden_real
    }

    datos["sesiones"].append(sesion)

    if st.session_state.orden_real:
        datos["dias"][dia_id]["ultima_rutina"] = st.session_state.orden_real

    guardar_datos(datos)

    st.session_state.seleccion_sesion = []
    st.session_state.completados = []
    st.session_state.ejercicio_actual = None
    st.session_state.serie_actual = 1
    st.session_state.orden_real = []
    st.session_state.inicio_sesion = None


def mostrar_historial(datos):
    ej_id = st.session_state.ejercicio_actual
    e = datos["ejercicios"][ej_id]

    if st.button("← Volver"):
        cambiar_pantalla("dia")

    st.title(f"Historial — {e['nombre']}")

    rows = [h for h in datos["historial"] if h["ejercicio_id"] == ej_id]

    if not rows:
        st.info("Este ejercicio todavía no tiene historial.")
        return

    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def mostrar_editar(datos):
    ej_id = st.session_state.ejercicio_actual
    e = datos["ejercicios"][ej_id]

    if st.button("← Volver"):
        cambiar_pantalla("gestionar_ejercicios")

    st.title(f"Editar — {e['nombre']}")

    dias_labels = {
        "lunes": "Lunes",
        "martes": "Martes",
        "miercoles": "Miércoles",
        "jueves": "Jueves",
        "viernes": "Viernes"
    }

    dia_actual_index = list(dias_labels.keys()).index(e["dia"])

    with st.form("editar_ejercicio"):
        nuevo_nombre = st.text_input("Nombre", value=e["nombre"])
        nuevo_dia_label = st.selectbox(
            "Día",
            list(dias_labels.values()),
            index=dia_actual_index
        )
        nuevo_musculo = st.text_input("Músculo", value=e["musculo"])
        nuevo_peso = st.text_input("Peso", value=e["peso"])
        nuevas_series = st.number_input(
            "Series",
            min_value=1,
            max_value=20,
            value=int(e["series"])
        )
        nuevas_reps = st.number_input(
            "Reps",
            min_value=1,
            max_value=100,
            value=int(e["reps"])
        )
        nota = st.text_area("Nota")
        guardar = st.form_submit_button("Guardar cambios")

    if guardar:
        old = e.copy()

        nuevo_dia_id = [k for k, v in dias_labels.items() if v == nuevo_dia_label][0]

        cambio_progreso = (
            old["peso"] != nuevo_peso
            or int(old["series"]) != int(nuevas_series)
            or int(old["reps"]) != int(nuevas_reps)
        )

        if cambio_progreso:
            datos["historial"].append({
                "fecha": datetime.now().strftime("%Y-%m-%d"),
                "ejercicio_id": ej_id,
                "ejercicio": old["nombre"],
                "antes": formato_ejercicio(old),
                "despues": f"{nuevo_peso} · {int(nuevas_series)}x{int(nuevas_reps)}",
                "nota": nota
            })

        datos["ejercicios"][ej_id]["nombre"] = nuevo_nombre.strip()
        datos["ejercicios"][ej_id]["dia"] = nuevo_dia_id
        datos["ejercicios"][ej_id]["musculo"] = nuevo_musculo.strip()
        datos["ejercicios"][ej_id]["peso"] = nuevo_peso.strip()
        datos["ejercicios"][ej_id]["series"] = int(nuevas_series)
        datos["ejercicios"][ej_id]["reps"] = int(nuevas_reps)

        guardar_datos(datos)

        st.success("Ejercicio actualizado.")
        cambiar_pantalla("gestionar_ejercicios")


def mostrar_sesiones(datos):
    if st.button("← Volver"):
        cambiar_pantalla("home")

    st.title("Sesiones guardadas")

    if not datos["sesiones"]:
        st.info("Todavía no hay sesiones.")
        return

    tabla = []

    for s in datos["sesiones"]:
        tabla.append({
            "Fecha": s["fecha"],
            "Día": s["dia"],
            "Duración": f"{s['duracion_min']} min",
            "Ejercicios": " → ".join(s["ejercicios"])
        })

    st.dataframe(pd.DataFrame(tabla), use_container_width=True)


def mostrar_nuevo_ejercicio(datos):
    if st.button("← Volver"):
        cambiar_pantalla("home")

    st.title("Añadir ejercicio")

    dias_labels = {
        "lunes": "Lunes",
        "martes": "Martes",
        "miercoles": "Miércoles",
        "jueves": "Jueves",
        "viernes": "Viernes"
    }

    with st.form("nuevo_ejercicio"):
        nombre = st.text_input("Nombre del ejercicio")
        dia_label = st.selectbox("Día", list(dias_labels.values()))
        musculo = st.text_input("Músculo")
        peso = st.text_input("Peso inicial", value="0 kg")
        series = st.number_input("Series", min_value=1, max_value=10, value=3)
        reps = st.number_input("Reps", min_value=1, max_value=100, value=10)

        guardar = st.form_submit_button("Añadir")

    if guardar:
        if not nombre.strip():
            st.warning("Escribe un nombre.")
            return

        dia_id = [k for k, v in dias_labels.items() if v == dia_label][0]

        nuevo_id = (
            nombre.lower()
            .replace(" ", "_")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ñ", "n")
        )

        contador_id = 1
        base_id = nuevo_id

        while nuevo_id in datos["ejercicios"]:
            contador_id += 1
            nuevo_id = f"{base_id}_{contador_id}"

        datos["ejercicios"][nuevo_id] = {
            "nombre": nombre,
            "dia": dia_id,
            "musculo": musculo,
            "peso": peso,
            "series": int(series),
            "reps": int(reps)
        }

        guardar_datos(datos)
        st.success("Ejercicio añadido.")
        cambiar_pantalla("home")

def mostrar_gestionar_ejercicios(datos):
    if st.button("← Volver"):
        cambiar_pantalla("home")

    st.title("Gestionar ejercicios")
    st.caption("Desde aquí puedes crear, editar o eliminar ejercicios.")

    st.divider()

    st.subheader("Crear nuevo ejercicio")

    dias_labels = {
        "lunes": "Lunes",
        "martes": "Martes",
        "miercoles": "Miércoles",
        "jueves": "Jueves",
        "viernes": "Viernes"
    }

    with st.form("crear_ejercicio"):
        nombre = st.text_input("Nombre del ejercicio")
        dia_label = st.selectbox("Día", list(dias_labels.values()))
        musculo = st.text_input("Músculo", placeholder="Ejemplo: Pecho, Bíceps, Pierna...")
        peso = st.text_input("Carga / peso", placeholder="Ejemplo: 30 kg, Peso corporal, 12.5 kg...")
        series = st.number_input("Series", min_value=1, max_value=20, value=3)
        reps = st.number_input("Repeticiones", min_value=1, max_value=100, value=10)

        crear = st.form_submit_button("Crear ejercicio")

    if crear:
        if not nombre.strip():
            st.warning("Escribe un nombre para el ejercicio.")
            return

        if not musculo.strip():
            st.warning("Escribe el músculo del ejercicio.")
            return

        if not peso.strip():
            st.warning("Escribe la carga o peso.")
            return

        dia_id = [k for k, v in dias_labels.items() if v == dia_label][0]

        nuevo_id = (
            nombre.lower()
            .strip()
            .replace(" ", "_")
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ñ", "n")
        )

        base_id = nuevo_id
        contador = 2

        while nuevo_id in datos["ejercicios"]:
            nuevo_id = f"{base_id}_{contador}"
            contador += 1

        datos["ejercicios"][nuevo_id] = {
            "nombre": nombre.strip(),
            "dia": dia_id,
            "musculo": musculo.strip(),
            "peso": peso.strip(),
            "series": int(series),
            "reps": int(reps)
        }

        guardar_datos(datos)
        st.success("Ejercicio creado correctamente.")
        st.rerun()

    st.divider()

    st.subheader("Ejercicios existentes")

    if not datos["ejercicios"]:
        st.info("Todavía no has creado ningún ejercicio.")
        return

    dias_orden = ["lunes", "martes", "miercoles", "jueves", "viernes"]

    for dia_id in dias_orden:
        dia = datos["dias"][dia_id]

        ejercicios_dia = [
            (ej_id, e)
            for ej_id, e in datos["ejercicios"].items()
            if e["dia"] == dia_id
        ]

        if not ejercicios_dia:
            continue

        st.markdown(f"### {dia['nombre']}")

        for ej_id, e in ejercicios_dia:
            with st.expander(f"{e['nombre']} — {e['peso']} · {e['series']}x{e['reps']}"):
                nuevo_nombre = st.text_input(
                    "Nombre",
                    value=e["nombre"],
                    key=f"nombre_edit_{ej_id}"
                )

                nuevo_musculo = st.text_input(
                    "Músculo",
                    value=e["musculo"],
                    key=f"musculo_edit_{ej_id}"
                )

                nuevo_peso = st.text_input(
                    "Carga / peso",
                    value=e["peso"],
                    key=f"peso_edit_{ej_id}"
                )

                nuevas_series = st.number_input(
                    "Series",
                    min_value=1,
                    max_value=20,
                    value=int(e["series"]),
                    key=f"series_edit_{ej_id}"
                )

                nuevas_reps = st.number_input(
                    "Repeticiones",
                    min_value=1,
                    max_value=100,
                    value=int(e["reps"]),
                    key=f"reps_edit_{ej_id}"
                )

                nuevo_dia_label = st.selectbox(
                    "Día",
                    list(dias_labels.values()),
                    index=list(dias_labels.keys()).index(e["dia"]),
                    key=f"dia_edit_{ej_id}"
                )

                col_guardar, col_copiar, col_borrar = st.columns(3)

                with col_guardar:
                    if st.button("Guardar cambios", key=f"guardar_edit_{ej_id}", use_container_width=True):
                        old = e.copy()

                        nuevo_dia_id = [k for k, v in dias_labels.items() if v == nuevo_dia_label][0]

                        cambio_progreso = (
                            old["peso"] != nuevo_peso
                            or int(old["series"]) != int(nuevas_series)
                            or int(old["reps"]) != int(nuevas_reps)
                        )

                        if cambio_progreso:
                            datos["historial"].append({
                                "fecha": datetime.now().strftime("%Y-%m-%d"),
                                "ejercicio_id": ej_id,
                                "ejercicio": old["nombre"],
                                "antes": formato_ejercicio(old),
                                "despues": f"{nuevo_peso} · {int(nuevas_series)}x{int(nuevas_reps)}",
                                "nota": "Cambio manual desde gestionar ejercicios"
                            })

                        datos["ejercicios"][ej_id]["nombre"] = nuevo_nombre.strip()
                        datos["ejercicios"][ej_id]["musculo"] = nuevo_musculo.strip()
                        datos["ejercicios"][ej_id]["peso"] = nuevo_peso.strip()
                        datos["ejercicios"][ej_id]["series"] = int(nuevas_series)
                        datos["ejercicios"][ej_id]["reps"] = int(nuevas_reps)
                        datos["ejercicios"][ej_id]["dia"] = nuevo_dia_id

                        guardar_datos(datos)
                        st.success("Ejercicio actualizado.")
                        st.rerun()
                with col_copiar:
                    if st.button("📋 Copiar ejercicio", key=f"copiar_{ej_id}", use_container_width=True):
                        nuevo_id_base = f"{ej_id}_copia"
                        nuevo_id = nuevo_id_base
                        contador = 2

                        while nuevo_id in datos["ejercicios"]:
                            nuevo_id = f"{nuevo_id_base}_{contador}"
                            contador += 1

                        nuevo_ejercicio = e.copy()
                        nuevo_ejercicio["nombre"] = e["nombre"]

                        datos["ejercicios"][nuevo_id] = nuevo_ejercicio

                        guardar_datos(datos)

                        st.session_state.ejercicio_actual = nuevo_id
                        st.success("Ejercicio copiado. Ahora cambia solo el día y guarda.")
                        cambiar_pantalla("editar")

                with col_borrar:
                    confirmar = st.checkbox(
                        "Confirmar eliminar",
                        key=f"confirmar_borrar_{ej_id}"
                    )

                    if st.button("Eliminar", key=f"borrar_{ej_id}", use_container_width=True):
                        if not confirmar:
                            st.warning("Marca la casilla de confirmar antes de eliminar.")
                        else:
                            # Quitar de últimas rutinas si estaba ahí
                            for d_id, d in datos["dias"].items():
                                if ej_id in d["ultima_rutina"]:
                                    d["ultima_rutina"] = [
                                        x for x in d["ultima_rutina"]
                                        if x != ej_id
                                    ]

                            # Quitar de ejercicios
                            del datos["ejercicios"][ej_id]

                            # También quitamos sus cambios del historial
                            datos["historial"] = [
                                h for h in datos["historial"]
                                if h.get("ejercicio_id") != ej_id
                            ]

                            guardar_datos(datos)
                            st.success("Ejercicio eliminado.")
                            st.rerun()
init_state()
datos = cargar_datos()

pantalla = st.session_state.pantalla

if pantalla == "home":
    mostrar_home(datos)
elif pantalla == "dia":
    mostrar_dia(datos)
elif pantalla == "sesion":
    mostrar_sesion(datos)
elif pantalla == "ejercicio_activo":
    mostrar_ejercicio_activo(datos)
elif pantalla == "descanso_serie":
    mostrar_descanso_serie()
elif pantalla == "resumen_ejercicio":
    mostrar_resumen_ejercicio(datos)
elif pantalla == "descanso_ejercicio":
    mostrar_descanso_ejercicio()
elif pantalla == "historial":
    mostrar_historial(datos)
elif pantalla == "editar":
    mostrar_editar(datos)
elif pantalla == "sesiones":
    mostrar_sesiones(datos)
elif pantalla == "nuevo_ejercicio":
    mostrar_nuevo_ejercicio(datos)
elif pantalla == "gestionar_ejercicios":
    mostrar_gestionar_ejercicios(datos)