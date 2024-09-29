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

    if 'xml_content' not in session:
        return render_template('archivo.html', message='Por favor, carga un archivo XML primero.', resultados=CustomList())

    xml_content = session['xml_content']
    root = ET.fromstring(xml_content)

    for maquina in root.findall('Maquina'):
        nombre_maquina = maquina.find('NombreMaquina').text
        if nombre_maquina == maquina_seleccionada:
            tiempo_ensamblaje = int(maquina.find('TiempoEnsamblaje').text)
            num_lineas = int(maquina.find('CantidadLineasProduccion').text)

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
                    
                    for segundo in range(tiempo_ensamblaje):
                        fila_tiempo = Resultado(f"{segundo + 1}{'er' if segundo == 0 else 'do' if segundo == 1 else 'er'}. Segundo", CustomList())
                        
                        acciones_realizadas = CustomList()
                        for _ in range(num_lineas):
                            acciones_realizadas.add(False)
                        
                        for instruccion_index in range(instrucciones.size()):
                            instruccion_actual = instrucciones.get(instruccion_index)
                            
                            # Skip completed instructions
                            if instruccion_actual == "COMPLETED":
                                continue
                            
                            linea_actual, componente_actual = obtener_linea_y_componente(instruccion_actual)
                            
                            if linea_actual <= num_lineas:
                                brazo_actual = brazos.get(linea_actual - 1)
                                accion = "No hacer nada"
                                
                                if not acciones_realizadas.get(linea_actual - 1):
                                    if brazo_actual < componente_actual:
                                        brazo_actual += 1
                                        accion = f"Mover brazo – componente {brazo_actual}"
                                        acciones_realizadas.update(linea_actual - 1, True)
                                    elif brazo_actual > componente_actual:
                                        brazo_actual -= 1
                                        accion = f"Mover brazo – componente {brazo_actual}"
                                        acciones_realizadas.update(linea_actual - 1, True)
                                    elif brazo_actual == componente_actual:
                                        # Verificar si todas las instrucciones anteriores se han completado
                                        can_assemble = True
                                        for prev_index in range(instruccion_index):
                                            prev_instruccion = instrucciones.get(prev_index)
                                            if prev_instruccion != "COMPLETED":
                                                prev_linea, prev_componente = obtener_linea_y_componente(prev_instruccion)
                                                prev_brazo = brazos.get(prev_linea - 1)
                                                if prev_brazo != prev_componente:
                                                    can_assemble = False
                                                    break
                                        
                                        if can_assemble:
                                            accion = f"Ensamblar componente {componente_actual}"
                                            acciones_realizadas.update(linea_actual - 1, True)
                                            instrucciones.update(instruccion_index, "COMPLETED")
                                
                                brazos.update(linea_actual - 1, brazo_actual)
                                
                                if fila_tiempo.lineas.size() < linea_actual:
                                    fila_tiempo.lineas.add(accion)
                                else:
                                    fila_tiempo.lineas.update(linea_actual - 1, accion)
                        
                        resultados.add(fila_tiempo)
                        
                        # Verificar si todas las instrucciones se han completado
                        all_completed = True
                        for i in range(instrucciones.size()):
                            if instrucciones.get(i) != "COMPLETED":
                                all_completed = False
                                break
                        
                        if all_completed:
                            break

    return render_template('archivo.html', resultados=resultados, maquinas=CustomList())

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

if __name__ == '__main__':
    app.run(debug=True)