from flask import Flask, render_template, request, redirect, url_for
import xml.etree.ElementTree as ET
from utils import CustomList

app = Flask(__name__)


@app.route('/')
def index():
    return redirect(url_for('archivo'))

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
