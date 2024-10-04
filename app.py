from flask import Flask, render_template, request, redirect, url_for, session, send_file
import xml.etree.ElementTree as ET
from utils import CustomList, Resultado, Nodo
import io
import os
from graphviz import Digraph
import xml.dom.minidom

app = Flask(__name__)
app.secret_key = 'una_clave_secreta_muy_segura'  # Necesario para usar sesiones

# Variable global para almacenar las máquinas
global_maquinas = CustomList()

# Agregar una variable global para el historial
global_historial = CustomList()

@app.route('/')
def index():
    return redirect(url_for('archivo'))

@app.route('/archivo', methods=['GET', 'POST'])
def archivo():
    global global_maquinas
    message = None

    if request.method == 'POST':
        if 'file' not in request.files:
            message = 'No se encontró ningún archivo.'
        else:
            file = request.files['file']
            if file.filename == '':
                message = 'No se seleccionó ningún archivo.'
            elif file and file.filename.endswith('.xml'):
                try:
                    xml_content = file.read()
                    root = ET.fromstring(xml_content)

                    # Procesar el nuevo XML y agregar/actualizar información
                    for maquina in root.findall('Maquina'):
                        nombre_maquina = maquina.find('NombreMaquina').text
                        productos = CustomList()

                        # Buscar si la máquina ya existe
                        maquina_existente = None
                        for i in range(global_maquinas.size()):
                            if global_maquinas.get(i).get(0) == nombre_maquina:
                                maquina_existente = global_maquinas.get(i)
                                break

                        if maquina_existente:
                            # Actualizar productos existentes
                            productos_existentes = maquina_existente.get(1)
                            for producto in maquina.find('ListadoProductos').findall('Producto'):
                                nombre_producto = producto.find('nombre').text
                                if nombre_producto not in productos_existentes:
                                    productos_existentes.add(nombre_producto)
                        else:
                            # Agregar nueva máquina
                            for producto in maquina.find('ListadoProductos').findall('Producto'):
                                nombre_producto = producto.find('nombre').text
                                productos.add(nombre_producto)

                            maquina_info = CustomList()
                            maquina_info.add(nombre_maquina)
                            maquina_info.add(productos)
                            global_maquinas.add(maquina_info)

                    session['xml_content'] = xml_content.decode('utf-8')
                    message = 'Archivo XML cargado y agregado correctamente.'
                except ET.ParseError:
                    message = 'Error al procesar el archivo XML.'
            else:
                message = 'Por favor, sube un archivo con extensión .xml.'

    maquina_seleccionada = session.get('maquina_seleccionada', '')
    producto_seleccionado = session.get('producto_seleccionado', '')

    return render_template('archivo.html', message=message, maquinas=global_maquinas,
                           maquina_seleccionada=maquina_seleccionada,
                           producto_seleccionado=producto_seleccionado)
    

def generate_assembly_graph(instrucciones_originales, tiempo_actual, tiempo_total, resultados):
    if tiempo_actual >= tiempo_total:
        return None

    # Crear el grafo
    dot = Digraph(comment='Pending Assembly Steps')
    dot.attr(rankdir='LR')

    # Listas personalizadas
    pasos_pendientes = CustomList()
    componentes_necesarios = CustomList()
    componentes_realizados = CustomList()
    componentes_ensamblando_actual = CustomList()  # Nueva lista para componentes siendo ensamblados en el tiempo actual

    # Contar cuántos ensamblajes necesita cada componente
    for i in range(instrucciones_originales.size()):
        paso = instrucciones_originales.get(i)
        componente = obtener_componente_de_paso(paso)
        
        encontrado = False
        for j in range(componentes_necesarios.size()):
            comp = componentes_necesarios.get(j)
            if comp.componente == componente:
                comp.cantidad += 1
                encontrado = True
                break
        
        if not encontrado:
            nuevo_comp = ComponenteContador(componente, 1)
            componentes_necesarios.add(nuevo_comp)

    # Procesar resultados y identificar componentes en ensamblaje actual
    for i in range(resultados.size()):
        resultado = resultados.get(i)
        
        # Reiniciar la lista de componentes en ensamblaje actual para cada nuevo tiempo
        if i == resultados.size() - 1:  # Si estamos en el último resultado (tiempo actual)
            componentes_ensamblando_actual = CustomList()
        
        for j in range(resultado.lineas.size()):
            accion = resultado.lineas.get(j)
            if "Ensamblar" in accion:
                componente = obtener_componente_de_accion(accion)
                
                # Si estamos en el último resultado, añadir a la lista de ensamblaje actual
                if i == resultados.size() - 1:
                    componentes_ensamblando_actual.add(componente)
                
                # Actualizar componentes realizados
                encontrado = False
                for k in range(componentes_realizados.size()):
                    comp = componentes_realizados.get(k)
                    if comp.componente == componente:
                        comp.cantidad += 1
                        encontrado = True
                        break
                
                if not encontrado:
                    nuevo_comp = ComponenteContador(componente, 1)
                    componentes_realizados.add(nuevo_comp)

    # Determinar qué pasos están pendientes
    for i in range(instrucciones_originales.size()):
        paso = instrucciones_originales.get(i)
        componente_actual = obtener_componente_de_paso(paso)
        
        # Verificar si el componente está siendo ensamblado actualmente
        esta_ensamblando_actual = False
        for j in range(componentes_ensamblando_actual.size()):
            if componentes_ensamblando_actual.get(j) == componente_actual:
                esta_ensamblando_actual = True
                break

        # Si el componente está siendo ensamblado actualmente, añadir el paso
        if esta_ensamblando_actual:
            pasos_pendientes.add(paso)
            continue

        # Si no está siendo ensamblado actualmente, verificar si aún necesita más ensamblajes
        cantidad_necesaria = 0
        cantidad_realizada = 0
        
        for j in range(componentes_necesarios.size()):
            comp = componentes_necesarios.get(j)
            if comp.componente == componente_actual:
                cantidad_necesaria = comp.cantidad
                break
        
        for j in range(componentes_realizados.size()):
            comp = componentes_realizados.get(j)
            if comp.componente == componente_actual:
                cantidad_realizada = comp.cantidad
                break
        
        if cantidad_realizada < cantidad_necesaria:
            pasos_pendientes.add(paso)

    # Si no hay pasos pendientes, no generar el grafo
    if pasos_pendientes.size() == 0:
        return None

    # Crear nodos y conexiones en el grafo para los pasos pendientes
    for i in range(pasos_pendientes.size()):
        paso_actual = pasos_pendientes.get(i)
        dot.node(str(i), paso_actual, shape='box')
        if i > 0:
            dot.edge(str(i-1), str(i))
    
    return dot

# Las clases auxiliares y funciones adicionales permanecen igual
class ComponenteContador:
    def __init__(self, componente, cantidad):
        self.componente = componente
        self.cantidad = cantidad

def obtener_componente_de_accion(accion):
    partes = accion.split()
    for parte in partes:
        if parte.isdigit():
            return int(parte)
    return None

def obtener_componente_de_paso(paso):
    _, componente = obtener_linea_y_componente(paso)
    return componente

class HistorialEntry:
    def __init__(self, maquina, producto, tiempo_total, resultados):
        self.maquina = maquina
        self.producto = producto
        self.tiempo_total = tiempo_total
        self.resultados = resultados

def generar_xml_salida():
    # Crear el elemento raíz
    raiz = ET.Element("SalidaSimulacion")
    
    # Para cada máquina en global_maquinas
    for i in range(global_maquinas.size()):
        info_maquina = global_maquinas.get(i)
        nombre_maquina = info_maquina.get(0)
        productos = info_maquina.get(1)  
        
        # Crear elemento de máquina
        elem_maquina = ET.SubElement(raiz, "Maquina")
        elem_nombre = ET.SubElement(elem_maquina, "Nombre")
        elem_nombre.text = nombre_maquina
        
        # Crear listado de productos
        listado_productos = ET.SubElement(elem_maquina, "ListadoProductos")
        
        # Encontrar resultados de simulación para cada producto en global_historial
        for j in range(global_historial.size()):
            entrada_historial = global_historial.get(j)
            
            if entrada_historial.maquina == nombre_maquina:
                # Crear elemento de producto
                elem_producto = ET.SubElement(listado_productos, "Producto")
                
                # Añadir nombre del producto
                nombre_producto = ET.SubElement(elem_producto, "Nombre")
                nombre_producto.text = entrada_historial.producto
                
                # Añadir tiempo total
                tiempo_total = ET.SubElement(elem_producto, "TiempoTotal")
                tiempo_total.text = str(entrada_historial.tiempo_total)
                
                # Crear elemento de elaboración óptima
                elaboracion_optima = ET.SubElement(elem_producto, "ElaboracionOptima")
                
                # Añadir pasos de tiempo
                for k in range(entrada_historial.resultados.size()):
                    resultado = entrada_historial.resultados.get(k)
                    elem_tiempo = ET.SubElement(elaboracion_optima, "Tiempo")
                    elem_tiempo.set("NoSegundo", str(k + 1))
                    
                    # Añadir líneas de ensamblaje
                    for l in range(resultado.lineas.size()):
                        elem_linea = ET.SubElement(elem_tiempo, "LineaEnsamblaje")
                        elem_linea.set("NoLinea", str(l + 1))
                        elem_linea.text = resultado.lineas.get(l)
    
    # Crear cadena XML y formatearla
    xml_str = ET.tostring(raiz, encoding='unicode', method='xml')
    xml_formateado = formatear_xml(xml_str)
    
    # Guardar en archivo
    ruta_archivo = 'static/simulacion_salida.xml'
    escribir_archivo(ruta_archivo, xml_formateado)
    
    return xml_formateado

def formatear_xml(xml_str):
    """Función para formatear la cadena XML con indentación adecuada"""
    dom = xml.dom.minidom.parseString(xml_str)
    xml_formateado = dom.toprettyxml(indent='  ')
    
    # Convertir el resultado en una lista de líneas
    lineas = CustomList()
    for linea in xml_formateado.split('\n'):
        lineas.add(linea)
    
    # Crear el resultado final
    resultado = CustomList()
    resultado.add('<?xml version="1.0"?>')
    
    for i in range(1, lineas.size()):
        linea = lineas.get(i)
        if linea.strip():  # Si la línea no está vacía
            resultado.add(linea)
    
    # Unir todas las líneas con saltos de línea
    salida_final = ''
    for i in range(resultado.size()):
        salida_final += resultado.get(i)
        if i < resultado.size() - 1:
            salida_final += '\n'
    
    return salida_final

def escribir_archivo(ruta, contenido):
    """Función para escribir el contenido en un archivo"""
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(contenido)

@app.route('/construir', methods=['POST'])
def construir():
    global global_maquinas
    global global_historial
    
    maquina_seleccionada = request.form.get('maquina')
    producto_seleccionado = request.form.get('producto')
    tiempo_seleccionado = request.form.get('tiempo', 'optimo')
    
    # Guardar las selecciones en la sesión
    session['maquina_seleccionada'] = maquina_seleccionada
    session['producto_seleccionada'] = producto_seleccionado
    
    resultados = CustomList()
    tiempo_total = 0

    if 'xml_content' not in session:
        return render_template('archivo.html', message='Por favor, carga un archivo XML primero.', resultados=CustomList())

    xml_content = session['xml_content']
    root = ET.fromstring(xml_content)

    for maquina in root.findall('Maquina'):
        nombre_maquina = maquina.find('NombreMaquina').text
        if nombre_maquina == maquina_seleccionada:
            num_lineas = int(maquina.find('CantidadLineasProduccion').text)
            tiempo_ensamblaje = int(maquina.find('TiempoEnsamblaje').text)

            for producto in maquina.find('ListadoProductos').findall('Producto'):
                nombre_producto = producto.find('nombre').text
                if nombre_producto == producto_seleccionado:
                    elaboracion = producto.find('elaboracion').text.strip().split()
                    
                    instrucciones = CustomList()
                    for paso in elaboracion:
                        instrucciones.add(paso)
                    
                    brazos = CustomList()
                    for _ in range(num_lineas):
                        brazos.add(0)
                    
                    segundo = 1
                    ensamblaje_actual = CustomList()
                    for _ in range(num_lineas):
                        ensamblaje_actual.add(0)

                    while True:
                        fila_tiempo = Resultado(f"{segundo}{'er' if segundo == 1 else 'do' if segundo == 2 else 'er'}. Segundo", CustomList())
                        for _ in range(num_lineas):
                            fila_tiempo.lineas.add("No hace nada")
                        
                        ensamblaje_realizado = False
                        
                        for linea in range(num_lineas):
                            instruccion_actual = None
                            for i in range(instrucciones.size()):
                                if instrucciones.get(i) != "COMPLETED":
                                    linea_instruccion, _ = obtener_linea_y_componente(instrucciones.get(i))
                                    if linea_instruccion - 1 == linea:
                                        instruccion_actual = instrucciones.get(i)
                                        instruccion_index = i
                                        break
                            
                            if instruccion_actual:
                                _, componente_actual = obtener_linea_y_componente(instruccion_actual)
                                brazo_actual = brazos.get(linea)
                                
                                if brazo_actual < componente_actual:
                                    brazo_actual += 1
                                    fila_tiempo.lineas.update(linea, f"Mover brazo – Componente {brazo_actual}")
                                    brazos.update(linea, brazo_actual)
                                elif brazo_actual > componente_actual:
                                    brazo_actual -= 1
                                    fila_tiempo.lineas.update(linea, f"Mover brazo – Componente {brazo_actual}")
                                    brazos.update(linea, brazo_actual)
                                elif brazo_actual == componente_actual and not ensamblaje_realizado:
                                    # Verificar si es el turno de esta instrucción
                                    can_assemble = True
                                    for j in range(instruccion_index):
                                        if instrucciones.get(j) != "COMPLETED":
                                            can_assemble = False
                                            break
                                    
                                    if can_assemble:
                                        if ensamblaje_actual.get(linea) < tiempo_ensamblaje:
                                            fila_tiempo.lineas.update(linea, f"Ensamblar - Componente {componente_actual}")
                                            ensamblaje_actual.update(linea, ensamblaje_actual.get(linea) + 1)
                                            ensamblaje_realizado = True
                                        
                                        if ensamblaje_actual.get(linea) == tiempo_ensamblaje:
                                            instrucciones.update(instruccion_index, "COMPLETED")
                                            ensamblaje_actual.update(linea, 0)
                        
                        resultados.add(fila_tiempo)
                        
                        all_completed = True
                        for i in range(instrucciones.size()):
                            if instrucciones.get(i) != "COMPLETED":
                                all_completed = False
                                break
                        
                        if all_completed:
                            tiempo_total = segundo
                            break
                        
                        segundo += 1

    # Filtrar resultados basados en el tiempo seleccionado
    try:
        tiempo_mostrado = int(tiempo_seleccionado)
    except ValueError:
        tiempo_mostrado = tiempo_total

    # Si el tiempo seleccionado es mayor que el tiempo total, agregamos pasos adicionales con "No hace nada"
    resultados_filtrados = CustomList()
    if tiempo_mostrado > tiempo_total:
        # Mostrar todos los resultados normales
        for i in range(resultados.size()):
            resultados_filtrados.add(resultados.get(i))
        
        # Añadir "No hace nada" en los tiempos adicionales
        for t in range(tiempo_total + 1, tiempo_mostrado + 1):
            fila_tiempo = Resultado(f"{t}{'er' if t == 1 else 'do' if t == 2 else 'er'}. Segundo", CustomList())
            for _ in range(num_lineas):
                fila_tiempo.lineas.add("No hace nada")
            resultados_filtrados.add(fila_tiempo)
    else:
        # Solo mostrar hasta el tiempo seleccionado
        for i in range(min(tiempo_mostrado, resultados.size())):
            resultados_filtrados.add(resultados.get(i))

    # Generar el grafo de ensamblaje
    instrucciones_originales = CustomList()
    elaboracion_list = CustomList()
    for paso in elaboracion:
        elaboracion_list.add(paso)
    
    for i in range(elaboracion_list.size()):
        instrucciones_originales.add(elaboracion_list.get(i))
    
    dot = generate_assembly_graph(instrucciones_originales, tiempo_mostrado, tiempo_total, resultados_filtrados)
    if dot:
        graph_filename = f'static/assembly_graph_{tiempo_mostrado}.gv'
        dot.render(graph_filename, format='png', cleanup=True)
        graph_image = f'assembly_graph_{tiempo_mostrado}.gv.png'
    else:
        graph_image = None
    
 # Al final de la función, antes del return, agregar:
    entrada_historial = HistorialEntry(
        maquina_seleccionada,
        producto_seleccionado,
        tiempo_total,
        resultados_filtrados
    )
    global_historial.add(entrada_historial)
    
    generar_xml_salida()
    
    return render_template('archivo.html', 
                          resultados=resultados_filtrados, 
                          maquinas=global_maquinas,
                          maquina_seleccionada=maquina_seleccionada, 
                          producto_seleccionado=producto_seleccionado,
                          tiempo_total=tiempo_total,
                          tiempo_mostrado=tiempo_mostrado,
                          graph_image=graph_image)

def obtener_linea_y_componente(paso):
    linea = ""
    componente = ""
    estado = "linea"

    for char in paso:
        if char == 'L':
            estado = "linea"
        elif char == 'C':
            estado = "componente"
        elif estado == "linea":
            linea += char
        elif estado == "componente":
            componente += char

    return int(linea), int(componente)

# Modificar la ruta de reportes para mostrar el historial
@app.route('/reportes')
def reportes():
    return render_template('reportes.html', historial=global_historial)

@app.route('/ayuda')
def ayuda():
    return render_template('ayuda.html')

@app.route('/descargar-reporte')
def descargar_reporte():
    # Crear un StringIO para almacenar el contenido HTML renderizado
    html_content = render_template('reportes.html', historial=global_historial)
    
    # Crear un objeto BytesIO para enviar el archivo
    buffer = io.BytesIO()
    buffer.write(html_content.encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='text/html',
        as_attachment=True,
        download_name='reporte_ensamblaje.html'
    )
    
@app.route('/descargar-xml')
def descargar_xml():
    try:
        xml_path = 'static/simulacion_salida.xml'
        if os.path.exists(xml_path):
            return send_file(
                xml_path,
                mimetype='application/xml',
                as_attachment=True,
                download_name='simulacion_salida.xml'
            )
        else:
            return "No se ha generado ningún archivo XML de salida.", 404
    except Exception as e:
        return f"Error al descargar el archivo: {str(e)}", 500

@app.route('/reset', methods=['POST'])
def reset():
    global global_maquinas
    global global_historial
    global_maquinas = CustomList()
    global_historial = CustomList()
    session.clear()
    return redirect(url_for('archivo'))

if __name__ == '__main__':
    app.run(debug=True)