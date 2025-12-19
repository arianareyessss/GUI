import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import socket
import threading
import time
import json
import queue

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
        #self.conveyor_speed = 0
        self.esp_status = 0  # 0=stop, 1=running, 2=error
        
        # Configuración de comunicación TCP
        self.tcp_host = "192.168.1.100"  # IP del ESP32
        self.tcp_port = 8080
        self.socket = None
        self.receive_thread = None
        self.data_queue = queue.Queue()
        self.data_timer = None  # Timer para pedir datos automáticamente
        
        # Crear widgets
        self.setup_gui()
        
        # Iniciar thread para procesar datos recibidos
        self.process_thread = threading.Thread(target=self.process_received_data, daemon=True)
        self.process_thread.start()
        
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
        
        #self.conveyor_indicator = tk.Label(status_frame, text="CINTA DETENIDA", fg="#C33B80", font=("Arial", 12))
        #self.conveyor_indicator.grid(row=0, column=1, padx=20)
        
        # Velocidad actual
        #self.speed_indicator = tk.Label(status_frame, text="VELOCIDAD: 0%", fg="#812E58", font=("Arial", 12))
        #self.speed_indicator.grid(row=0, column=2, padx=20)
        
        # Marco izquierdo - Control y visualización
        left_frame = ttk.LabelFrame(self.tab_control_frame, text="Control y Visualización", padding=15)
        left_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # Botones de control
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(pady=10)
        
        self.start_button = tk.Button(control_frame, text="INICIAR SISTEMA", 
                                      command=self.start_system, 
                                      bg="#D691B4", fg="#F8EAF2", 
                                      font=("Arial", 12, "bold"),
                                      height=2, width=15)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = tk.Button(control_frame, text="DETENER SISTEMA", 
                                     command=self.stop_system, 
                                     bg="#D691B4", fg="#F8EAF2", 
                                     font=("Arial", 12, "bold"),
                                     height=2, width=15,
                                     state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        #self.reset_button = tk.Button(control_frame, text="RESET CONTADORES", 
        #                              command=self.reset_counters, 
        #                              bg="#D691B4", fg="#F8EAF2", 
        #                              font=("Arial", 12, "bold"),
        #                              height=2, width=15)
        #self.reset_button.pack(side="left", padx=5)
        
        # Botón para pedir datos manualmente
        #self.get_data_button = tk.Button(control_frame, text="ACTUALIZAR DATOS", 
        #                                 command=self.request_data, 
        #                                 bg="#C33B80", fg="#F8EAF2", 
        #                                 font=("Arial", 12, "bold"),
        #                                 height=2, width=15)
        #self.get_data_button.pack(side="left", padx=5)
        
        # Indicador de color actual
        color_frame = ttk.LabelFrame(left_frame, text="COLOR DETECTADO", padding=10)
        color_frame.pack(pady=20, fill="x")
        
        self.color_display = tk.Label(color_frame, text=self.current_color, 
                                      font=("Arial", 24, "bold"), 
                                      bg="#D691B4", width=15, height=2, fg="#F8EAF2")
        self.color_display.pack()
        
        # Marco de conteo en tiempo real
        count_frame = tk.LabelFrame(left_frame, text="CONTEO EN TIEMPO REAL", 
                           fg="#812E58",
                           bg="#F0F0F0",
                           font=("Arial", 10, "bold"),
                           padx=10, pady=10)
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
        self.total_label = tk.Label(total_frame, text="0", font=("Arial", 14, "bold"), fg="#812E58")
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
            ("Cinta", " CINTA DETENIDA", "#D691B4"),
            ("Detección", "DETECCION INACTIVA", "#D691B4"),
            ("Clasificación", "CLASIFICACION INACTIVA", "#D691B4"),
            ("Comunicación", "COMUNICACIÓN: DESCONECTADO", "#D691B4")
        ]
        
        for led_name, led_text, default_color in led_states:
            frame = ttk.Frame(indicators_frame)
            frame.pack(fill="x", pady=5)
            
            led = tk.Canvas(frame, width=20, height=20)
            led.create_oval(2, 2, 18, 18, fill=default_color)
            led.pack(side="left", padx=10)
            
            label = tk.Label(frame, text=led_text, fg="#812E58")
            label.pack(side="left")
            
            self.leds[led_name] = (led, label)
        
        # Información del sistema
        info_frame = ttk.LabelFrame(right_frame, text="Información del Sistema", padding=10)
        info_frame.pack(pady=10, fill="x")
        
        self.info_text = scrolledtext.ScrolledText(info_frame, height=8, width=40)
        self.info_text.pack(fill="both", expand=True)
        self.info_text.insert("1.0", "Sistema listo.\nEsperando conexión con ESP32...\n")
        self.info_text.config(state="disabled")
        
        # Alarmas
        alarm_frame = ttk.LabelFrame(right_frame, text="Panel de Alarmas", padding=10)
        alarm_frame.pack(pady=10, fill="both", expand=True)
        
        self.alarm_text = scrolledtext.ScrolledText(alarm_frame, height=6, width=40)
        self.alarm_text.pack(fill="both", expand=True)
        self.alarm_text.insert("1.0", "No hay alarmas activas.\n")
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
        
        tk.Button(toolbar, text="Limpiar Logs", command=self.clear_logs, 
                 bg="#D691B4", fg="#F8EAF2").pack(side="left", padx=5)
        tk.Button(toolbar, text="Exportar Logs", command=self.export_logs,
                 bg="#D691B4", fg="#F8EAF2").pack(side="left", padx=5)
        tk.Button(toolbar, text="Buscar Error", command=self.search_errors,
                 bg="#D691B4", fg="#F8EAF2").pack(side="left", padx=5)
        
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
        
        self.connect_button = tk.Button(conn_frame, text="Conectar", 
                                       command=self.toggle_connection, 
                                       bg="#D691B4", fg="#F8EAF2")
        self.connect_button.grid(row=0, column=2, rowspan=2, padx=20)
        
        # Configuración de actualización
        update_frame = ttk.LabelFrame(config_frame, text="Configuración de Actualización", padding=15)
        update_frame.pack(fill="x", pady=20)
        
        #ttk.Label(update_frame, text="Intervalo de datos (ms):").grid(row=0, column=0, sticky="w", pady=5)
        #self.update_interval = ttk.Spinbox(update_frame, from_=100, to=5000, width=10)
        #self.update_interval.set(1000)
        #self.update_interval.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        self.auto_update_var = tk.BooleanVar(value=True)
        self.auto_update_cb = tk.Checkbutton(update_frame, text="Actualización automática", 
                                            variable=self.auto_update_var,
                                            command=self.toggle_auto_update,
                                            fg="#812E58")
        self.auto_update_cb.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")
        
        # Botones de acción
        action_frame = ttk.Frame(config_frame)
        action_frame.pack(pady=20)
        
        tk.Button(action_frame, text="Guardar Configuración", 
                 command=self.save_config, 
                 bg="#D691B4", fg="#F8EAF2").pack(side="left", padx=10)
        tk.Button(action_frame, text="Restaurar Valores", 
                 command=self.restore_config,
                 bg="#D691B4", fg="#F8EAF2").pack(side="left", padx=10)
        tk.Button(action_frame, text="Probar Conexión", 
                 command=self.test_connection,
                 bg="#C33B80", fg="#F8EAF2").pack(side="left", padx=10)
    
    # ========== FUNCIONES DE CONEXIÓN ==========
    
    def toggle_connection(self):
        if not self.connected:
            self.connect_to_esp32()
        else:
            self.disconnect_from_esp32()
    
    def connect_to_esp32(self):
        if self.connected:
            return
            
        self.connect_button.config(state="disabled", text="Conectando...")
        
        host = self.ip_entry.get()
        port = int(self.port_entry.get())
        
        threading.Thread(target=self._connect_thread, args=(host, port), daemon=True).start()
    
    def _connect_thread(self, host, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            self.root.after(0, lambda: self.log_event("Comunicación", f"Conectando a {host}:{port}..."))
            
            sock.connect((host, port))
            sock.settimeout(1)
            
            self.root.after(0, self._connection_successful, sock, host, port)
            
        except socket.timeout:
            self.root.after(0, self._connection_failed, f"Timeout: No se pudo conectar a {host}:{port}")
        except ConnectionRefusedError:
            self.root.after(0, self._connection_failed, f"Conexión rechazada por {host}")
        except Exception as e:
            self.root.after(0, self._connection_failed, f"Error conectando a {host}: {str(e)}")
    
    def _connection_successful(self, sock, host, port):
        self.socket = sock
        self.connected = True
        self.tcp_host = host
        self.tcp_port = port
        
        self.connect_button.config(state="normal", text="Desconectar", bg="#C33B80", fg="#F8EAF2")
        self.connection_indicator.config(text=" CONECTADO", fg="#C33B80")
        self.update_led("Comunicación", "#C33B80", "CONECTADO")
        
        self.log_event("Comunicación", f"¡Conectado a ESP32 en {host}:{port}!")
        self.update_info_text(f"Conexión establecida con ESP32\nIP: {host}:{port}\n")
        
        self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.receive_thread.start()
        
        # Iniciar actualización automática de datos
        if self.auto_update_var.get():
            self.start_auto_update()
        
        # Pedir datos iniciales
        self.request_data()
    
    def _connection_failed(self, error_msg):
        self.connect_button.config(state="normal", text="Conectar", bg="#D691B4", fg="#F8EAF2")
        self.connection_indicator.config(text="DESCONECTADO", fg="#C33B80")
        
        self.log_event("Errores", error_msg)
        messagebox.showerror("Error de Conexión", error_msg)
    
    def disconnect_from_esp32(self):
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            
            self.connected = False
            self.system_running = False
            self.connect_button.config(text="Conectar", bg="#D691B4", fg="#F8EAF2")
            self.connection_indicator.config(text="DESCONECTADO", fg="#C33B80")
            self.conveyor_indicator.config(text="CINTA DETENIDA", fg="#C33B80")
            self.update_led("Comunicación", "#D691B4", "DESCONECTADO")
            self.update_led("Cinta", "#D691B4", "DETENIDA")
            
            self.log_event("Comunicación", "Desconectado de ESP32")
            self.update_info_text("Desconectado de ESP32\n")
            
            # Detener actualización automática
            self.stop_auto_update()
            
            # Deshabilitar botones
            self.start_button.config(state="normal", bg="#D691B4")
            self.stop_button.config(state="disabled", bg="#D691B4")
            
        except Exception as e:
            self.log_event("Errores", f"Error al desconectar: {str(e)}")
    
    def test_connection(self):
        host = self.ip_entry.get()
        port = int(self.port_entry.get())
        
        def test():
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(3)
                test_sock.connect((host, port))
                test_sock.close()
                self.root.after(0, lambda: messagebox.showinfo("Prueba Exitosa", 
                    f"Conexión exitosa a {host}:{port}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Prueba Fallida", 
                    f"No se pudo conectar a {host}:{port}\nError: {str(e)}"))
        
        threading.Thread(target=test, daemon=True).start()
    
    # ========== RECEPCIÓN DE DATOS ==========
    
    def receive_data(self):
        buffer = ""
        while self.connected and self.socket:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                    
                data_str = data.decode('utf-8', errors='ignore')
                if data_str:
                    buffer += data_str
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            self.data_queue.put(line)
                            
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError):
                break
            except Exception as e:
                if self.connected:
                    self.root.after(0, lambda: self.log_event("Errores", f"Error recepción: {str(e)}"))
                break
        
        if self.connected:
            self.root.after(0, self.disconnect_from_esp32)
    
    def process_received_data(self):
        while True:
            try:
                data = self.data_queue.get(timeout=0.1)
                self.root.after(0, self.handle_esp_data, data)
            except queue.Empty:
                continue
    
    def handle_esp_data(self, data):
        try:
            if data.startswith('{'):
                json_data = json.loads(data)
                self.process_json_data(json_data)
            else:
                self.log_event("Comunicación", f"Mensaje ESP32: {data}")
                
        except json.JSONDecodeError:
            self.log_event("Comunicación", f"Datos recibidos: {data}")
        except Exception as e:
            self.log_event("Errores", f"Error procesando datos ESP32: {str(e)}")
    
    def process_json_data(self, json_data):
        msg_type = json_data.get("type", "")
        
        if msg_type == "init":
            self.log_event("Comunicación", f"ESP32: {json_data.get('message', 'Listo')}")
            self.update_info_text(f"ESP32 inicializado\nModo FAKE activado\n")
            
        elif msg_type == "data" or msg_type == "sensor_data":
            # Actualizar contadores
            red = json_data.get("red", 0)
            green = json_data.get("green", 0)
            blue = json_data.get("blue", 0)
            other = json_data.get("other", 0)
            total = json_data.get("total", 0)
            
            self.box_count["ROJO"] = red
            self.box_count["VERDE"] = green
            self.box_count["AZUL"] = blue
            self.box_count["OTRO"] = other
            self.total_count = total
            
            # Actualizar GUI
            self.update_counters()
            
            # Actualizar color actual
            last_color = json_data.get("last_color", "NINGUNO")
            self.update_color_display(last_color)
            
            # Actualizar velocidad
            #speed = json_data.get("speed", 0)
            #self.conveyor_speed = speed
            #self.speed_indicator.config(text=f"VELOCIDAD: {speed}%")
            
            # Actualizar estado
            status = json_data.get("status", 0)
            self.esp_status = status
            
            # Actualizar LEDs según estado
            if status == 1:  # RUNNING
                self.update_led("Cinta", "#C33B80", "CINTA EN MOVIMIENTO")
                self.update_led("Detección", "#C33B80", "DETECCIÓN ACTIVA")
                self.update_led("Clasificación", "#C33B80", "CLASIFICACIÓN ACTIVA")
            elif status == 0:  # STOPPED
                self.update_led("Cinta", "#D691B4", "CINTA DETENIDA")
                self.update_led("Detección", "#D691B4", "DETECCION INACTIVA")
                self.update_led("Clasificación", "#D691B4", "CLASIFICACIÓN INACTIVA")
            
            # Log
            self.log_event("Datos", 
                f"ROJO:{red} VERDE:{green} AZUL:{blue} OTRO:{other} TOTAL:{total}")
            
        elif msg_type == "start_ack":
            self.log_event("Sistema", json_data.get("message", "Sistema iniciado"))
            self.conveyor_indicator.config(text="CINTA EN MOVIMIENTO", fg="#C33B80")
            self.update_info_text("Sistema iniciado\nGenerando datos fake...\n")
            
        elif msg_type == "stop_ack":
            self.log_event("Sistema", json_data.get("message", "Sistema detenido"))
            self.conveyor_indicator.config(text="CINTA DETENIDA", fg="#C33B80")
            self.update_info_text("Sistema detenido\n")
            
        elif msg_type == "reset_ack":
            self.log_event("Sistema", json_data.get("message", "Contadores reseteados"))
            
        elif msg_type == "error":
            error_msg = json_data.get("message", "Error desconocido")
            self.log_event("Errores", f"ESP32: {error_msg}")
            self.update_alarm_text(f"Error: {error_msg}\n")
    
    # ========== ENVÍO DE COMANDOS ==========
    
    def send_command(self, command):
        if self.connected and self.socket:
            try:
                self.socket.sendall(f"{command}\n".encode('utf-8'))
                self.log_event("Comunicación", f"Comando enviado: {command}")
            except Exception as e:
                self.log_event("Errores", f"Error enviando comando: {str(e)}")
                self.disconnect_from_esp32()
    
    def request_data(self):
        if self.connected:
            self.send_command("GET_DATA")
    
    def start_system(self):
        if not self.connected:
            messagebox.showwarning("Advertencia", "Conecta primero con la ESP32")
            return
        
        self.send_command("START")
        self.system_running = True
        self.start_button.config(state="disabled", bg="#812E58")
        self.stop_button.config(state="normal", bg="#C33B80")
        
    def stop_system(self):
        if self.connected:
            self.send_command("STOP")
        self.system_running = False
        self.start_button.config(state="normal", bg="#D691B4")
        self.stop_button.config(state="disabled", bg="#D691B4")
    
    # ========== ACTUALIZACIÓN AUTOMÁTICA ==========
    
    def start_auto_update(self):
        if self.connected and self.auto_update_var.get():
            interval = int(self.update_interval.get())
            self.data_timer = self.root.after(interval, self._auto_update)
    
    def _auto_update(self):
        if self.connected and self.auto_update_var.get():
            self.request_data()
            interval = int(self.update_interval.get())
            self.data_timer = self.root.after(interval, self._auto_update)
    
    def stop_auto_update(self):
        if self.data_timer:
            self.root.after_cancel(self.data_timer)
            self.data_timer = None
    
    def toggle_auto_update(self):
        if self.auto_update_var.get():
            self.start_auto_update()
        else:
            self.stop_auto_update()
    
    # ========== ACTUALIZACIÓN GUI ==========
    
    def update_counters(self):
        for color in self.box_count:
            self.count_labels[color].config(text=str(self.box_count[color]))
        self.total_label.config(text=str(self.total_count))
    
    def update_color_display(self, color):
        self.current_color = color
        self.color_display.config(text=color)
        
        color_map = {
            "ROJO": "#D691B4",
            "VERDE": "#D691B4",
            "AZUL": "#D691B4",
            "OTRO": "#D691B4",
            "NINGUNO": "#D691B4"
        }
        
        bg_color = color_map.get(color, "#D691B4")
        fg_color = "#F8EAF2"
        
        self.color_display.config(bg=bg_color, fg=fg_color)
        
        if color != "NINGUNO":
            self.log_event("Detecciones", f"Color detectado: {color}")
    
    def update_led(self, led_name, color, text):
        if led_name in self.leds:
            canvas, label = self.leds[led_name]
            canvas.delete("all")
            canvas.create_oval(2, 2, 18, 18, fill=color)
            label.config(text=text, fg="#812E58")
    
    def update_info_text(self, message):
        self.info_text.config(state="normal")
        self.info_text.insert("end", f"{datetime.now().strftime('%H:%M:%S')} - {message}")
        self.info_text.see("end")
        self.info_text.config(state="disabled")
    
    def update_alarm_text(self, message):
        self.alarm_text.config(state="normal")
        self.alarm_text.insert("end", f"{datetime.now().strftime('%H:%M:%S')} - {message}")
        self.alarm_text.see("end")
        self.alarm_text.config(state="disabled")
    
    def log_event(self, event_type, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{event_type}] {message}\n"
        
        self.log_text.config(state="normal")
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        
        if event_type == "Errores" or "ERROR" in message.upper():
            self.update_alarm_text(f"{message}\n")
    
    # ========== FUNCIONES ADICIONALES ==========
    
    def reset_counters(self):
        if self.connected:
            self.send_command("RESET_COUNTERS")
        
        for color in self.box_count:
            self.box_count[color] = 0
            self.count_labels[color].config(text="0")
        
        self.total_count = 0
        self.total_label.config(text="0")
        self.log_event("Sistema", "Contadores reseteados localmente")
    
    def clear_logs(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self.log_event("Sistema", "Logs limpiados")
    
    def export_logs(self):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs_conveyor_{timestamp}.txt"
            
            with open(filename, "w", encoding='utf-8') as f:
                logs = self.log_text.get("1.0", "end")
                f.write(logs)
            
            self.log_event("Sistema", f"Logs exportados a {filename}")
            messagebox.showinfo("Éxito", f"Logs exportados a {filename}")
        except Exception as e:
            self.log_event("Errores", f"Error exportando logs: {str(e)}")
    
    def search_errors(self):
        logs = self.log_text.get("1.0", "end")
        error_count = logs.upper().count("ERROR")
        
        self.log_text.config(state="normal")
        self.log_text.tag_remove("error", "1.0", "end")
        
        start_idx = "1.0"
        while True:
            start_idx = self.log_text.search("ERROR", start_idx, stopindex="end", nocase=True)
            if not start_idx:
                break
            end_idx = f"{start_idx}+{len('ERROR')}c"
            self.log_text.tag_add("error", start_idx, end_idx)
            start_idx = end_idx
        
        self.log_text.tag_config("error", background="#F8DAEB", foreground="#C33B80")
        self.log_text.config(state="disabled")
        
        messagebox.showinfo("Búsqueda de Errores", f"Se encontraron {error_count} errores en los logs")
    
    def save_config(self):
        try:
            config = {
                "tcp_host": self.ip_entry.get(),
                "tcp_port": int(self.port_entry.get()),
                "update_interval": int(self.update_interval.get()),
                "auto_update": self.auto_update_var.get()
            }
            
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            
            self.log_event("Sistema", "Configuración guardada")
            messagebox.showinfo("Éxito", "Configuración guardada")
            
        except Exception as e:
            self.log_event("Errores", f"Error guardando configuración: {str(e)}")
    
    def restore_config(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            
            self.ip_entry.delete(0, tk.END)
            self.ip_entry.insert(0, config.get("tcp_host", "10.179.36.130"))
            
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, str(config.get("tcp_port", 8080)))
            
            self.update_interval.delete(0, tk.END)
            self.update_interval.insert(0, str(config.get("update_interval", 1000)))
            
            self.auto_update_var.set(config.get("auto_update", True))
            
            self.log_event("Sistema", "Configuración restaurada")
            messagebox.showinfo("Éxito", "Configuración restaurada")
            
        except FileNotFoundError:
            self.log_event("Sistema", "No se encontró archivo de configuración")
        except Exception as e:
            self.log_event("Errores", f"Error restaurando configuración: {str(e)}")
    
    def on_closing(self):
        if self.connected:
            self.disconnect_from_esp32()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ConveyorControlGUI(root)
    
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    menubar = tk.Menu(root, bg="#F8DAEB", fg="#C33B80")
    root.config(menu=menubar)
    
    file_menu = tk.Menu(menubar, tearoff=0, bg="#F8DAEB", fg="#C33B80")
    menubar.add_cascade(label="Archivo", menu=file_menu)
    file_menu.add_command(label="Exportar Logs", command=app.export_logs)
    file_menu.add_command(label="Guardar Configuración", command=app.save_config)
    file_menu.add_separator()
    file_menu.add_command(label="Salir", command=app.on_closing)
    
    system_menu = tk.Menu(menubar, tearoff=0, bg="#F8DAEB", fg="#C33B80")
    menubar.add_cascade(label="Sistema", menu=system_menu)
    system_menu.add_command(label="Conectar ESP32", command=app.connect_to_esp32)
    system_menu.add_command(label="Desconectar ESP32", command=app.disconnect_from_esp32)
    system_menu.add_separator()
    system_menu.add_command(label="Iniciar Sistema", command=app.start_system)
    system_menu.add_command(label="Detener Sistema", command=app.stop_system)
    system_menu.add_command(label="Resetear Contadores", command=app.reset_counters)
    system_menu.add_separator()
    system_menu.add_command(label="Actualizar Datos", command=app.request_data)
    
    root.mainloop()

if __name__ == "__main__":
    main()