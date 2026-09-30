"""Script de validación para SismoAI Trainer Web."""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core'))

from bridge.api_bridge import ApiBridge

def main():
    print("=" * 60)
    print("SismoAI Trainer Web — Validación")
    print("=" * 60)

    # 1. Instanciar bridge
    print("\n[1] Instanciando ApiBridge...")
    bridge = ApiBridge()
    print("    OK: ApiBridge instanciado")

    # 2. Estado inicial
    print("\n[2] Verificando estado inicial del proyecto...")
    state = bridge.get_project_state()
    print(f"    Estado: {state['state']}")
    print(f"    Carpeta: {state['folder_path']}")

    # 3. Seleccionar carpeta Reference
    print("\n[3] Seleccionando carpeta Reference...")
    result = bridge._project.select_folder('Reference')
    print(f"    Resultado: {result}")

    # Esperar escaneo
    print("    Esperando escaneo...")
    time.sleep(3)

    # 4. Estado después del escaneo
    print("\n[4] Verificando estado después del escaneo...")
    state = bridge.get_project_state()
    print(f"    Estado: {state['state']}")
    print(f"    Archivos: {state['file_count']}")
    print(f"    Eventos: {state['event_count']}")

    # 5. Escanear archivos
    print("\n[5] Escaneando archivos BIN...")
    files = bridge.scan_files()
    print(f"    Archivos encontrados: {len(files)}")
    for f in files[:3]:
        print(f"      - {f['name']}: {f['status_text']} ({f['size_text']})")

    # 6. Obtener resumen de calidad del primer archivo
    if files:
        print("\n[6] Obteniendo resumen de calidad...")
        quality = bridge.get_quality_summary(files[0]['name'])
        if 'error' not in quality:
            print(f"    Archivo: {quality['name']}")
            print(f"    Estado: {quality['status_text']}")
            print(f"    Eventos: {quality['event_count_text']}")
        else:
            print(f"    Error: {quality['error']}")

    # 7. Obtener estado de datos
    print("\n[7] Verificando estado de datos...")
    data_state = bridge.get_data_state()
    print(f"    Estado: {data_state['state']}")
    print(f"    Archivos: {data_state['file_count']}")

    # 8. Obtener archivos para análisis
    print("\n[8] Obteniendo archivos para análisis...")
    analysis_files = bridge.get_analysis_files()
    print(f"    Archivos válidos: {len(analysis_files)}")
    for f in analysis_files[:3]:
        print(f"      - {f['name']}")

    # 9. Seleccionar archivo para análisis
    if analysis_files:
        print("\n[9] Seleccionando archivo para análisis...")
        result = bridge.select_analysis_file(analysis_files[0]['name'])
        print(f"    Resultado: {result}")

        time.sleep(2)

        # 10. Obtener estado de análisis
        print("\n[10] Verificando estado de análisis...")
        analysis_state = bridge.get_analysis_state()
        print(f"    Estado: {analysis_state['state']}")
        print(f"    Tiene selección: {analysis_state['has_selection']}")
        print(f"    Archivo: {analysis_state['selected_file_name']}")

        # 11. Obtener datos del evento
        if analysis_state['has_selection']:
            print("\n[11] Obteniendo datos del evento...")
            event_data = bridge.get_analysis_event_data()
            if 'error' not in event_data:
                print(f"    Geófono: {len(event_data['geophone_times'])} muestras")
                print(f"    MPU: {len(event_data['mpu_times'])} muestras")
            else:
                print(f"    Error: {event_data['error']}")

            # 12. Obtener métricas
            print("\n[12] Obteniendo métricas de señal...")
            metrics = bridge.get_analysis_metrics()
            if 'error' not in metrics:
                print(f"    Sensor seleccionado: {metrics['selected_sensor']}")
            else:
                print(f"    Error: {metrics['error']}")

    print("\n" + "=" * 60)
    print("Validación completada exitosamente")
    print("=" * 60)

if __name__ == '__main__':
    main()
