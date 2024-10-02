from flask import Flask, render_template, request, redirect, url_for, session
import xml.etree.ElementTree as ET
from utils import CustomList, Resultado, Nodo
import io
from graphviz import Digraph

app = Flask(__name__)
app.secret_key = 'una_clave_secreta_muy_segura'  # Necesario para usar sesiones

# Variable global para almacenar las máquinas
global_maquinas = CustomList()

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
    

def generate_assembly_graph(instrucciones_originales, tiempo_actual, tiempo_total):
    if tiempo_actual > tiempo_total:
        return None
    
    # Crear una copia de las instrucciones originales
    instrucciones = CustomList()
    for i in range(instrucciones_originales.size()):
        instrucciones.add(instrucciones_originales.get(i))
    
    # Simular el ensamblaje hasta el tiempo actual
    for segundo in range(1, tiempo_actual + 1):
        for i in range(instrucciones.size()):
            if instrucciones.get(i) != "COMPLETED":
                instrucciones.update(i, "COMPLETED")
                break

    # Crear el grafo
    dot = Digraph(comment='Assembly Steps')
    dot.attr(rankdir='LR')  # Establecer dirección de izquierda a derecha
    
    # Filtrar las instrucciones no completadas
    pasos_restantes = CustomList()
    for i in range(instrucciones.size()):
        if instrucciones.get(i) != "COMPLETED":
            pasos_restantes.add(instrucciones.get(i))
    
    # Si no hay pasos restantes, no generar el grafo
    if pasos_restantes.size() == 0:
        return None
    
    # Crear nodos y conexiones en línea
    for i in range(pasos_restantes.size()):
        paso_actual = pasos_restantes.get(i)
        dot.node(str(i), paso_actual, shape='box')
        if i > 0:
            dot.edge(str(i-1), str(i))
    
    return dot

@app.route('/construir', methods=['POST'])
def construir():
    global global_maquinas
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
    if tiempo_seleccionado.lower() == 'optimo':
        tiempo_mostrado = tiempo_total
    else:
        try:
            tiempo_mostrado = int(tiempo_seleccionado)
            if tiempo_mostrado > tiempo_total:
                tiempo_mostrado = tiempo_total
        except ValueError:
            tiempo_mostrado = tiempo_total

    resultados_filtrados = CustomList()
    for i in range(resultados.size()):
        if i < tiempo_mostrado:
            resultados_filtrados.add(resultados.get(i))

   # Después de procesar los resultados, generar el grafo
    instrucciones_originales = CustomList()
    elaboracion_list = CustomList()
    for paso in elaboracion:
        elaboracion_list.add(paso)
    
    for i in range(elaboracion_list.size()):
        instrucciones_originales.add(elaboracion_list.get(i))
    
    tiempo_mostrado = tiempo_total if tiempo_seleccionado.lower() == 'optimo' else int(tiempo_seleccionado)
    
    dot = generate_assembly_graph(instrucciones_originales, tiempo_mostrado, tiempo_total)
    if dot:
        graph_filename = f'static/assembly_graph_{tiempo_mostrado}.gv'
        dot.render(graph_filename, format='png', cleanup=True)
        graph_image = f'assembly_graph_{tiempo_mostrado}.gv.png'
    else:
        graph_image = None
    
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

@app.route('/reportes')
def reportes():
    return render_template('reportes.html')

@app.route('/ayuda')
def ayuda():
    return render_template('ayuda.html')

@app.route('/reset', methods=['POST'])
def reset():
    global global_maquinas
    global_maquinas = CustomList()
    session.clear()
    return redirect(url_for('archivo'))

if __name__ == '__main__':
    app.run(debug=True)