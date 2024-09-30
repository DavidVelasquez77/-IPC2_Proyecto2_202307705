from flask import Flask, render_template, request, redirect, url_for, session
import xml.etree.ElementTree as ET
from utils import CustomList, Resultado, Nodo
import io

app = Flask(__name__)
app.secret_key = 'una_clave_secreta_muy_segura'  # Necesario para usar sesiones

@app.route('/')
def index():
    return redirect(url_for('archivo'))

@app.route('/archivo', methods=['GET', 'POST'])
def archivo():
    message = None
    maquinas = CustomList()

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
                    session['xml_content'] = xml_content.decode('utf-8')  
                    root = ET.fromstring(xml_content)

                    for maquina in root.findall('Maquina'):
                        nombre_maquina = maquina.find('NombreMaquina').text
                        productos = CustomList()

                        for producto in maquina.find('ListadoProductos').findall('Producto'):
                            nombre_producto = producto.find('nombre').text
                            productos.add(nombre_producto)

                        maquina_info = CustomList()
                        maquina_info.add(nombre_maquina)
                        maquina_info.add(productos)
                        maquinas.add(maquina_info)

                    message = 'Archivo XML cargado correctamente.'
                except ET.ParseError:
                    message = 'Error al procesar el archivo XML.'
            else:
                message = 'Por favor, sube un archivo con extensión .xml.'

    return render_template('archivo.html', message=message, maquinas=maquinas)


@app.route('/construir', methods=['POST'])
def construir():
    maquina_seleccionada = request.form.get('maquina')
    producto_seleccionado = request.form.get('producto')    
    resultados = CustomList()
    tiempo_total = 0  # Inicializa una variable para el tiempo total

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
                            tiempo_total = segundo  # Asigna el tiempo total de ensamblaje
                            break   
                        
                        segundo += 1

    # Pasar el tiempo total al template
    return render_template('archivo.html', resultados=resultados, maquinas=CustomList(), 
                            maquina_seleccionada=maquina_seleccionada, producto_seleccionado=producto_seleccionado,
                            tiempo_total=tiempo_total)


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
    # Limpiar la sesión para eliminar cualquier dato cargado previamente
    session.clear()
    return redirect(url_for('archivo'))


if __name__ == '__main__':
    app.run(debug=True)