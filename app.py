from flask import Flask, render_template, request, redirect, url_for
import xml.etree.ElementTree as ET
from utils import CustomList  # Asumimos que CustomList está definida en utils.py

app = Flask(__name__)

@app.route('/') 
def index(): 
    return redirect(url_for('archivo'))
# Ruta para la página de inicio y carga de archivo
@app.route('/archivo', methods=['GET', 'POST'])
def archivo():
    message = None
    maquinas = CustomList()  # Usamos CustomList en lugar de una lista nativa
    
    if request.method == 'POST':
        if 'file' not in request.files:
            message = 'No se encontró ningún archivo.'
        else:
            file = request.files['file']
            if file.filename == '':
                message = 'No se seleccionó ningún archivo.'
            elif file and file.filename.endswith('.xml'):
                try:
                    tree = ET.parse(file)
                    root = tree.getroot()

                    # Recorrer las máquinas en el archivo XML
                    for maquina in root.findall('Maquina'):
                        nombre_maquina = maquina.find('NombreMaquina').text
                        productos = CustomList()
                        
                        # Recorrer los productos de cada máquina
                        for producto in maquina.find('ListadoProductos').findall('Producto'):
                            nombre_producto = producto.find('nombre').text
                            productos.add(nombre_producto)
                        
                        # Almacenar la máquina y sus productos en CustomList
                        maquinas.add((nombre_maquina, productos))
                    
                    message = 'Archivo XML cargado correctamente.'
                except ET.ParseError:
                    message = 'Error al procesar el archivo XML.'
            else:
                message = 'Por favor, sube un archivo con extensión .xml.'

    return render_template('archivo.html', message=message, maquinas=maquinas)

# Nueva ruta para manejar la simulación y generar la tabla
@app.route('/construir', methods=['POST'])
def construir():
    maquina_seleccionada = request.form.get('maquina')
    producto_seleccionado = request.form.get('producto')
    
    # Simulación de resultados
    resultados = CustomList()
    
    # Generar datos simulados para la tabla (esto puede ser reemplazado por la lógica real)
    for i in range(5):
        resultados.add({
            'tiempo': f'{i+1} horas',
            'lineas': f'Línea {i+1}'
        })

    # Renderizamos la plantilla con los resultados generados
    return render_template('archivo.html', resultados=resultados, maquinas=CustomList())

# Ruta para la página de "Reportes"
@app.route('/reportes')
def reportes():
    return render_template('reportes.html')

# Ruta para la página de "Ayuda"
@app.route('/ayuda')
def ayuda():
    return render_template('ayuda.html')

if __name__ == '__main__':
    app.run(debug=True)
