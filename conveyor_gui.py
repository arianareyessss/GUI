import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import socket
import threading
import time

class ConveyorControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Cinta Transportadora - Control y Monitoreo")
        self.root.geometry("1200x800")
        
        # Variables del sistema
        self.system_running = False
        self.connected = False
        self.current_color = "NINGUNO"
        self.box_count = {"ROJO": 0, "VERDE": 0, "AZUL": 0, "OTRO": 0}
        self.total_count = 0
        
        # Configuración de comunicación TCP (simulada)
        self.tcp_host = "192.168.1.100"  # IP de la ESP32
        self.tcp_port = 8080
        
        # Crear widgets
        self.setup_gui()
        
        # Iniciar thread para simulación de datos (para pruebas)
        self.simulation_thread = threading.Thread(target=self.simulate_data, daemon=True)
        self.simulation_thread.start()
        
    def setup_gui(self):
        # Crear pestañas
        self.tab_control = ttk.Notebook(self.root)
        
        # Pestaña 1: Control Principal
        self.tab_control_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_control_frame, text='Control Principal')
        
        # Pestaña 2: Historial y Logs
        self.tab_logs_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_logs_frame, text='Historial y Logs')
        
        # Pestaña 3: Configuración
        self.tab_config_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_config_frame, text='Configuración')
        
        self.tab_control.pack(expand=1, fill="both")
        
        # Configurar cada pestaña
        self.setup_control_tab()
        self.setup_logs_tab()
        self.setup_config_tab()
        
    def setup_control_tab(self):
        # Marco superior - Estado del sistema
        status_frame = ttk.LabelFrame(self.tab_control_frame, text="Estado del Sistema", padding=10)
        status_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        # Indicadores de estado
        self.connection_indicator = tk.Label(status_frame, text="DESCONECTADO", fg="#C33B80", font=("Arial", 12))
        self.connection_indicator.grid(row=0, column=0, padx=20)
        
        self.conveyor_indicator = tk.Label(status_frame, text="CINTA DETENIDA", fg="#C33B80", font=("Arial", 12))
        self.conveyor_indicator.grid(row=0, column=1, padx=20)
        
        # Marco izquierdo - Control y visualización
        left_frame = ttk.LabelFrame(self.tab_control_frame, text="Control y Visualización", 
                           padding=15)
        left_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # Botón de inicio/parada
        self.start_button = tk.Button(left_frame, text="INICIAR SISTEMA", 
                                      command=self.toggle_system, 
                                      bg="#D691B4", fg="#F8EAF2", 
                                      font=("Arial", 14, "bold"),
                                      height=2, width=20)
        self.start_button.pack(pady=10)
        
        # Indicador de color actual
        color_frame = ttk.LabelFrame(left_frame, text="COLOR DETECTADO", padding=10)
        color_frame.pack(pady=20, fill="x")
        
        self.color_display = tk.Label(color_frame, text=self.current_color, 
                                      font=("Arial", 24, "bold"), 
                                      bg="#D691B4", width=15, height=2, fg="#F8EAF2" )
        self.color_display.pack()
        
        # Marco de conteo en tiempo real
        count_frame = tk.LabelFrame(left_frame, text="CONTEO EN TIEMPO REAL", 
                           fg="#812E58",  # Rosado oscuro
                           bg="#F0F0F0",  # Fondo gris claro (opcional)
                           font=("Arial", 10, "bold"),  # (opcional)
                           padx=10, pady=10)  # padding con padx/pady
        count_frame.pack(pady=20, fill="x")
        
        self.count_labels = {}
        colors = ["ROJO", "VERDE", "AZUL", "OTRO"]
        for i, color in enumerate(colors):
            frame = ttk.Frame(count_frame)
            frame.pack(fill="x", pady=5)
            
            label = tk.Label(frame, text=f"{color}:", width=10, anchor="w", fg="#812E58")
            label.pack(side="left")
            
            count_label = tk.Label(frame, text="0", font=("Arial", 12, "bold"))
            count_label.pack(side="left", padx=10)
            
            self.count_labels[color] = count_label
        
        total_frame = ttk.Frame(count_frame)
        total_frame.pack(fill="x", pady=10)
        tk.Label(total_frame, text="TOTAL:", font=("Arial", 12, "bold"), fg="#812E58").pack(side="left")
        #tk.Label(total_frame, text="TOTAL:", font=("Arial", 12, "bold")).pack(side="left")
        self.total_label = tk.Label(total_frame, text="0", font=("Arial", 14, "bold"), fg="blue")
        self.total_label.pack(side="left", padx=10)
        
        # Marco derecho - Alertas y monitoreo
        right_frame = ttk.LabelFrame(self.tab_control_frame, text="Alertas y Monitoreo", padding=15)
        right_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        
        # Indicadores visuales
        indicators_frame = ttk.LabelFrame(right_frame, text="Indicadores de Estado", padding=10)
        indicators_frame.pack(pady=10, fill="x")
        
        # LEDs simulados
        self.leds = {}
        led_states = [
            ("Funcionamiento", "CINTA EN FUNCIONAMIENTO", "gray"),
            ("Detección", "COLOR DETECTADO", "gray"),
            ("Clasificación", "CLASIFICACIÓN REALIZADA", "gray"),
            ("Error", "SIN ERRORES", "gray")
        ]
        
        for led_name, led_text, default_color in led_states:
            frame = ttk.Frame(indicators_frame)
            frame.pack(fill="x", pady=5)
            
            led = tk.Canvas(frame, width=20, height=20)
            led.create_oval(2, 2, 18, 18, fill=default_color)
            led.pack(side="left", padx=10)
            
            label = tk.Label(frame, text=led_text)
            label.pack(side="left")
            
            self.leds[led_name] = (led, label)
        
        # Alarmas
        alarm_frame = ttk.LabelFrame(right_frame, text="Panel de Alarmas", padding=10)
        alarm_frame.pack(pady=20, fill="both", expand=True)
        
        self.alarm_text = scrolledtext.ScrolledText(alarm_frame, height=10, width=40)
        self.alarm_text.pack(fill="both", expand=True)
        self.alarm_text.insert("1.0", "Sistema listo. No hay alarmas activas.\n")
        self.alarm_text.config(state="disabled")
        
        # Configurar grid weights
        self.tab_control_frame.columnconfigure(0, weight=1)
        self.tab_control_frame.columnconfigure(1, weight=1)
        self.tab_control_frame.rowconfigure(1, weight=1)
        
    def setup_logs_tab(self):
        # Frame principal para logs
        logs_frame = ttk.Frame(self.tab_logs_frame, padding=10)
        logs_frame.pack(fill="both", expand=True)
        
        # Área de texto para historial
        self.log_text = scrolledtext.ScrolledText(logs_frame, height=25, width=100)
        self.log_text.pack(fill="both", expand=True)
        
        # Barra de herramientas para logs
        toolbar = ttk.Frame(logs_frame)
        toolbar.pack(fill="x", pady=5)
        
        tk.Button(toolbar, text="Limpiar Logs", command=self.clear_logs).pack(side="left", padx=5)
        tk.Button(toolbar, text="Exportar Logs", command=self.export_logs).pack(side="left", padx=5)
        tk.Button(toolbar, text="Buscar Error", command=self.search_errors).pack(side="left", padx=5)
        
        # Filtros para logs
        filter_frame = ttk.LabelFrame(logs_frame, text="Filtros", padding=10)
        filter_frame.pack(fill="x", pady=10)
        
        self.filter_vars = {}
        log_types = ["Detecciones", "Clasificaciones", "Errores", "Comunicación", "Sistema"]
        
        for i, log_type in enumerate(log_types):
            var = tk.BooleanVar(value=True)
            self.filter_vars[log_type] = var
            cb = tk.Checkbutton(filter_frame, text=log_type, variable=var, 
                               command=self.apply_log_filters)
            cb.grid(row=0, column=i, padx=10)
            
    def setup_config_tab(self):
        config_frame = ttk.Frame(self.tab_config_frame, padding=20)
        config_frame.pack(fill="both", expand=True)
        
        # Configuración de conexión
        conn_frame = ttk.LabelFrame(config_frame, text="Configuración de Conexión", padding=15)
        conn_frame.pack(fill="x", pady=10)
        
        ttk.Label(conn_frame, text="IP ESP32:").grid(row=0, column=0, sticky="w", pady=5)
        self.ip_entry = ttk.Entry(conn_frame, width=20)
        self.ip_entry.grid(row=0, column=1, padx=10, pady=5)
        self.ip_entry.insert(0, self.tcp_host)
        
        ttk.Label(conn_frame, text="Puerto:").grid(row=1, column=0, sticky="w", pady=5)
        self.port_entry = ttk.Entry(conn_frame, width=10)
        self.port_entry.grid(row=1, column=1, padx=10, pady=5)
        self.port_entry.insert(0, str(self.tcp_port))
        
        tk.Button(conn_frame, text="Conectar", command=self.connect_to_esp32).grid(row=0, column=2, rowspan=2, padx=20)
        
        # Configuración del sistema
        system_frame = ttk.LabelFrame(config_frame, text="Configuración del Sistema", padding=15)
        system_frame.pack(fill="x", pady=20)
        
        ttk.Label(system_frame, text="Velocidad cinta:").grid(row=0, column=0, sticky="w", pady=5)
        self.speed_slider = ttk.Scale(system_frame, from_=0, to=100, orient="horizontal")
        self.speed_slider.set(50)
        self.speed_slider.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        ttk.Label(system_frame, text="Umbral detección:").grid(row=1, column=0, sticky="w", pady=5)
        self.threshold_spinbox = ttk.Spinbox(system_frame, from_=0, to=100, width=10)
        self.threshold_spinbox.set(30)
        self.threshold_spinbox.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Botones de acción
        action_frame = ttk.Frame(config_frame)
        action_frame.pack(pady=20)
        
        tk.Button(action_frame, text="Guardar Configuración", 
                 command=self.save_config).pack(side="left", padx=10)
        tk.Button(action_frame, text="Restaurar Valores", 
                 command=self.restore_config).pack(side="left", padx=10)
        tk.Button(action_frame, text="Resetear Contadores", 
                 command=self.reset_counters).pack(side="left", padx=10)
        
        system_frame.columnconfigure(1, weight=1)
        
    def toggle_system(self):
        if not self.system_running:
            self.start_system()
        else:
            self.stop_system()
    
    def start_system(self):
        self.system_running = True
        self.start_button.config(text="DETENER SISTEMA", bg="#C33B80")
        self.conveyor_indicator.config(text="CINTA EN MOVIMIENTO", fg="#C33B80")
        self.update_led("Funcionamiento", "#C33B80", "CINTA EN FUNCIONAMIENTO")
        self.log_event("Sistema", "Sistema iniciado")
        
    def stop_system(self):
        self.system_running = False
        self.start_button.config(text="INICIAR SISTEMA", bg="#D691B4")
        self.conveyor_indicator.config(text="CINTA DETENIDA", fg="gray")
        self.update_led("Funcionamiento", "gray", "CINTA DETENIDA")
        self.log_event("Sistema", "Sistema detenido")
    
    def update_led(self, led_name, color, text):
        canvas, label = self.leds[led_name]
        canvas.delete("all")
        canvas.create_oval(2, 2, 18, 18, fill=color)
        label.config(text=text)
    
    def log_event(self, event_type, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{event_type}] {message}\n"
        
        # Actualizar área de logs
        self.log_text.config(state="normal")
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        
        # Actualizar panel de alarmas si es error
        if "ERROR" in message.upper():
            self.alarm_text.config(state="normal")
            self.alarm_text.insert("end", log_entry)
            self.alarm_text.see("end")
            self.alarm_text.config(state="disabled")
            self.update_led("Error", "red", "ERROR DETECTADO")
    
    def update_color_display(self, color):
        self.current_color = color
        self.color_display.config(text=color)
        
        # Cambiar color de fondo según el color detectado
        color_map = {
            "ROJO": "red",
            "VERDE": "green",
            "AZUL": "blue",
            "OTRO": "gray",
            "NINGUNO": "white"
        }
        self.color_display.config(bg=color_map.get(color, "white"))
        
        if color != "NINGUNO":
            self.update_led("Detección", "yellow", f"DETECTADO: {color}")
            self.log_event("Detecciones", f"Color detectado: {color}")
    
    def add_box(self, color):
        if color in self.box_count:
            self.box_count[color] += 1
            self.total_count += 1
            
            # Actualizar contadores
            self.count_labels[color].config(text=str(self.box_count[color]))
            self.total_label.config(text=str(self.total_count))
            
            # Actualizar LED de clasificación
            self.update_led("Clasificación", "blue", f"CLASIFICADO: {color}")
            self.log_event("Clasificaciones", f"Caja {color} clasificada. Total: {self.box_count[color]}")
    
    def connect_to_esp32(self):
        # Esta función simularía la conexión real con la ESP32
        try:
            # Simular conexión (en implementación real usaría socket)
            self.connected = True
            self.connection_indicator.config(text=" CONECTADO", fg="green")
            self.log_event("Comunicación", f"Conectado a ESP32 en {self.ip_entry.get()}:{self.port_entry.get()}")
            
            # Actualizar variables
            self.tcp_host = self.ip_entry.get()
            self.tcp_port = int(self.port_entry.get())
            
        except Exception as e:
            self.log_event("Errores", f"Error de conexión: {str(e)}")
    
    def clear_logs(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self.log_event("Sistema", "Logs limpiados")
    
    def export_logs(self):
        # Exportar logs a archivo
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs_conveyor_{timestamp}.txt"
            
            with open(filename, "w") as f:
                logs = self.log_text.get("1.0", "end")
                f.write(logs)
            
            self.log_event("Sistema", f"Logs exportados a {filename}")
        except Exception as e:
            self.log_event("Errores", f"Error exportando logs: {str(e)}")
    
    def search_errors(self):
        # Buscar errores en los logs
        logs = self.log_text.get("1.0", "end")
        error_count = logs.upper().count("ERROR")
        self.log_event("Sistema", f"Se encontraron {error_count} errores en los logs")
    
    def apply_log_filters(self):
        # Implementar filtros de logs
        pass
    
    def save_config(self):
        # Guardar configuración
        self.log_event("Sistema", "Configuración guardada")
    
    def restore_config(self):
        # Restaurar configuración por defecto
        self.log_event("Sistema", "Configuración restaurada")
    
    def reset_counters(self):
        # Resetear contadores
        for color in self.box_count:
            self.box_count[color] = 0
            self.count_labels[color].config(text="0")
        
        self.total_count = 0
        self.total_label.config(text="0")
        self.log_event("Sistema", "Contadores reseteados")
    
    def simulate_data(self):
        # Función para simular datos del sistema (solo para pruebas)
        colors = ["ROJO", "VERDE", "AZUL", "OTRO"]
        color_index = 0
        
        while True:
            time.sleep(3)  # Simular cada 3 segundos
            
            if self.system_running and self.connected:
                # Simular detección de color
                color = colors[color_index]
                self.update_color_display(color)
                
                # Simular clasificación después de 1 segundo
                self.root.after(1000, lambda c=color: self.add_box(c))
                
                color_index = (color_index + 1) % len(colors)
                
                # Simular error aleatorio
                import random
                if random.random() < 0.1:  # 10% de probabilidad de error
                    self.log_event("Errores", "ERROR: Sensor de color no responde")

# Función principal para ejecutar la aplicación
def main():
    root = tk.Tk()
    app = ConveyorControlGUI(root)
    
    # Agregar menú
   
     
    menubar = tk.Menu(root, bg="#F8DAEB", fg="#C33B80")  # Fondo rosado claro, texto rosado oscuro
    root.config(menu=menubar)

    file_menu = tk.Menu(menubar, tearoff=0, bg="#F8DAEB", fg="#C33B80")
    menubar.add_cascade(label="Salir", command=root.quit)  # Agrega esto para que aparezca
    #file_menu.add_command(label="Salir", command=root.quit)

    # Para los submenús también:
    #help_menu = tk.Menu(menubar, tearoff=0, bg="#F8DAEB", fg="#C33B80")
    #menubar.add_cascade(label="Ayuda", menu=help_menu)  # Descomenta esto
    #help_menu.add_command(label="Manual de Usuario")
    #help_menu.add_command(label="Acerca de")
    
    
    
    root.mainloop()

if __name__ == "__main__":
    main()