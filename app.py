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

                    lineas_ensamblaje = CustomList()
                    for _ in range(num_lineas):
                        lineas_ensamblaje.add(CustomList())

                    for paso in elaboracion:
                        linea, componente = obtener_linea_y_componente(paso)
                        linea_index = linea - 1
                        
                        lineas_ensamblaje.get(linea_index).add(f"Ensamblar componente {componente}")

                    for segundo in range(tiempo_ensamblaje):
                        fila_tiempo = Resultado(f"{segundo + 1}er. Segundo", CustomList())

                        for linea_index in range(num_lineas):
                            linea_actual = lineas_ensamblaje.get(linea_index)
                            if segundo < linea_actual.size():
                                accion = linea_actual.get(segundo)
                            else:
                                accion = "No hacer nada"
                            
                            fila_tiempo.lineas.add(accion)
                        
                        resultados.add(fila_tiempo)

    return render_template('archivo.html', resultados=resultados, maquinas=CustomList())

@app.route('/reportes')
def reportes():
    return render_template('reportes.html')

@app.route('/ayuda')
def ayuda():
    return render_template('ayuda.html')

if __name__ == '__main__':
    app.run(debug=True)