import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import socket
import threading
import time
import json
import queue
from collections import defaultdict

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
        self.detection_count = 0
        self.conveyor_speed = 75
        self.stm32_connected = False
        self.esp_status = 0
        self.last_detection_time = 0
        
        # Acumulador de datos en tiempo real (ahora acumulativo)
        self.realtime_counts = defaultdict(int)  # Esto mantendrá los valores acumulados
        self.realtime_detections = 0
        self.last_update_time = time.time()
        self.update_interval = 1.0
        
        # Configuración de comunicación TCP
        self.tcp_host = "192.168.4.1"  # IP del ESP32 en modo AP
        self.tcp_port = 8080
        self.socket = None
        
        self.receive_thread = None
        self.data_queue = queue.Queue()
        self.data_timer = None
        
        # Crear widgets
        self.setup_gui()
        
        # Iniciar thread para procesar datos recibidos
        self.process_thread = threading.Thread(target=self.process_received_data, daemon=True)
        self.process_thread.start()
        
        # Iniciar timer para acumulación de tiempo real
        self.start_realtime_timer()
        
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
        
        # Estado de conexiones
        conn_frame = ttk.Frame(status_frame)
        conn_frame.pack(pady=5)
        
        tk.Label(conn_frame, text="ESP32:", font=("Arial", 10), fg="#812E58").pack(side="left", padx=5)
        self.esp_indicator = tk.Label(conn_frame, text="DESCONECTADO", fg="#C33B80", font=("Arial", 10, "bold"))
        self.esp_indicator.pack(side="left", padx=20)
        
        tk.Label(conn_frame, text="STM32:", font=("Arial", 10), fg="#812E58").pack(side="left", padx=5)
        self.stm32_indicator = tk.Label(conn_frame, text="DESCONECTADO", fg="#C33B80", font=("Arial", 10, "bold"))
        self.stm32_indicator.pack(side="left", padx=20)
        
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
        
        # Botón de reset
        tk.Button(control_frame, text="RESETEAR CONTADORES", 
                 command=self.reset_counters,
                 bg="#C33B80", fg="#F8EAF2",
                 font=("Arial", 10, "bold"),
                 height=2, width=18).pack(side="left", padx=5)
        
        # Indicador de detección
        detection_frame = ttk.LabelFrame(left_frame, text="ESTADO DE DETECCIÓN", padding=10)
        detection_frame.pack(pady=10, fill="x")
        
        self.detection_indicator = tk.Label(detection_frame, text="NO DETECTADO", 
                                          font=("Arial", 14, "bold"), 
                                          bg="#D691B4", width=20, height=2, fg="#F8EAF2")
        self.detection_indicator.pack()
        
        # Indicador de color actual
        color_frame = ttk.LabelFrame(left_frame, text="COLOR DETECTADO", padding=10)
        color_frame.pack(pady=10, fill="x")
        
        self.color_display = tk.Label(color_frame, text=self.current_color, 
                                      font=("Arial", 24, "bold"), 
                                      bg="#D691B4", width=15, height=2, fg="#F8EAF2")
        self.color_display.pack()
        
        # Marco de conteo en tiempo real (modificado para mostrar acumulados)
        count_frame = tk.LabelFrame(left_frame, text="CONTEO EN TIEMPO REAL (Acumulado por intervalo)", 
                           fg="#812E58",
                           bg="#F0F0F0",
                           font=("Arial", 10, "bold"),
                           padx=10, pady=10)
        count_frame.pack(pady=20, fill="x")
        
        # Contadores en tiempo real
        self.realtime_labels = {}
        colors = ["ROJO", "VERDE", "AZUL", "OTRO"]
        
        # Detecciones en tiempo real
        det_frame = ttk.Frame(count_frame)
        det_frame.pack(fill="x", pady=2)
        tk.Label(det_frame, text="DETECCIONES:", width=12, anchor="w", fg="#812E58").pack(side="left")
        self.detection_realtime_label = tk.Label(det_frame, text="0", font=("Arial", 10))
        self.detection_realtime_label.pack(side="left", padx=10)
        
        for i, color in enumerate(colors):
            frame = ttk.Frame(count_frame)
            frame.pack(fill="x", pady=2)
            
            label = tk.Label(frame, text=f"{color}:", width=10, anchor="w", fg="#812E58")
            label.pack(side="left")
            
            count_label = tk.Label(frame, text="0", font=("Arial", 10))
            count_label.pack(side="left", padx=10)
            
            self.realtime_labels[color] = count_label
        
        # Marco de conteo total acumulado
        total_count_frame = tk.LabelFrame(left_frame, text="CONTEO TOTAL ACUMULADO", 
                           fg="#812E58",
                           bg="#F0F0F0",
                           font=("Arial", 10, "bold"),
                           padx=10, pady=10)
        total_count_frame.pack(pady=20, fill="x")
        
        # Detecciones totales
        det_total_frame = ttk.Frame(total_count_frame)
        det_total_frame.pack(fill="x", pady=2)
        tk.Label(det_total_frame, text="DETECCIONES:", width=12, anchor="w", fg="#812E58").pack(side="left")
        self.detection_total_label = tk.Label(det_total_frame, text="0", font=("Arial", 10, "bold"))
        self.detection_total_label.pack(side="left", padx=10)
        
        self.count_labels = {}
        for i, color in enumerate(colors):
            frame = ttk.Frame(total_count_frame)
            frame.pack(fill="x", pady=2)
            
            label = tk.Label(frame, text=f"{color}:", width=10, anchor="w", fg="#812E58")
            label.pack(side="left")
            
            count_label = tk.Label(frame, text="0", font=("Arial", 10, "bold"))
            count_label.pack(side="left", padx=10)
            
            self.count_labels[color] = count_label
        
        total_frame = ttk.Frame(total_count_frame)
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
            ("Sensor", "SENSOR INACTIVO", "#D691B4"),
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
        
        ttk.Label(update_frame, text="Intervalo de actualización (ms):").grid(row=0, column=0, sticky="w", pady=5)
        self.interval_entry = ttk.Entry(update_frame, width=10)
        self.interval_entry.grid(row=0, column=1, padx=10, pady=5)
        self.interval_entry.insert(0, "1000")
        
        self.auto_update_var = tk.BooleanVar(value=True)
        self.auto_update_cb = tk.Checkbutton(update_frame, text="Actualización automática", 
                                            variable=self.auto_update_var,
                                            command=self.toggle_auto_update,
                                            fg="#812E58")
        self.auto_update_cb.grid(row=1, column=0, columnspan=2, pady=5, sticky="w")
        
        # Botón de prueba STM32
        stm32_frame = ttk.LabelFrame(config_frame, text="Prueba STM32", padding=15)
        stm32_frame.pack(fill="x", pady=20)
        
        tk.Button(stm32_frame, text="Ping STM32", 
                 command=self.ping_stm32,
                 bg="#C33B80", fg="#F8EAF2").pack(side="left", padx=5)
        
        tk.Button(stm32_frame, text="Solicitar Estado", 
                 command=self.get_status,
                 bg="#D691B4", fg="#F8EAF2").pack(side="left", padx=5)
        
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
        self.esp_indicator.config(text="CONECTADO", fg="#C33B80")
        self.update_led("Comunicación", "#C33B80", "CONECTADO")
        
        self.log_event("Comunicación", f"¡Conectado a ESP32 en {host}:{port}!")
        self.update_info_text(f"Conexión establecida con ESP32\nIP: {host}:{port}\n")
        
        self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
        self.receive_thread.start()
        
        # Iniciar actualización automática de datos
        if self.auto_update_var.get():
            self.start_auto_update()
        
        # Solicitar estado inicial
        self.send_command("GET_STATUS")
    
    def _connection_failed(self, error_msg):
        self.connect_button.config(state="normal", text="Conectar", bg="#D691B4", fg="#F8EAF2")
        self.esp_indicator.config(text="DESCONECTADO", fg="#C33B80")
        
        self.log_event("Errores", error_msg)
        messagebox.showerror("Error de Conexión", error_msg)
    
    def disconnect_from_esp32(self):
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            
            self.connected = False
            self.system_running = False
            self.stm32_connected = False
            self.connect_button.config(text="Conectar", bg="#D691B4", fg="#F8EAF2")
            self.esp_indicator.config(text="DESCONECTADO", fg="#C33B80")
            self.stm32_indicator.config(text="DESCONECTADO", fg="#C33B80")
            self.update_led("Comunicación", "#D691B4", "DESCONECTADO")
            self.update_led("Cinta", "#D691B4", "DETENIDA")
            self.update_led("Sensor", "#D691B4", "SENSOR INACTIVO")
            
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
                # Procesar mensaje de DETECCIÓN
                if "DETECTADO" in data:
                    self.process_detection()
                    self.log_event("Detección", "Objeto detectado")
                # Procesar mensaje directo de color
                elif "Color:" in data:
                    color = data.split(":")[1].strip()
                    self.accumulate_realtime_count(color)
                    self.log_event("Color", f"Color detectado: {color}")
                else:
                    self.log_event("Comunicación", f"Mensaje ESP32: {data}")
                
        except json.JSONDecodeError:
            # Procesar mensaje directo
            if "DETECTADO" in data:
                self.process_detection()
                self.log_event("Detección", "Objeto detectado")
            elif "Color:" in data:
                color = data.split(":")[1].strip()
                self.accumulate_realtime_count(color)
                self.log_event("Color", f"Color detectado: {color}")
            else:
                self.log_event("Comunicación", f"Datos recibidos: {data}")
        except Exception as e:
            self.log_event("Errores", f"Error procesando datos ESP32: {str(e)}")
    
    def process_detection(self):
        """Procesa una detección de objeto"""
        self.detection_count += 1
        self.realtime_detections += 1
        self.last_detection_time = time.time()
        
        # Actualizar indicador visual
        self.detection_indicator.config(text="OBJETO DETECTADO", bg="#C33B80", fg="#F8EAF2")
        self.update_led("Sensor", "#C33B80", "SENSOR ACTIVO")
        
        # Programar regreso a estado normal después de 500ms
        self.root.after(500, self.reset_detection_indicator)
        
        # Actualizar etiquetas
        self.detection_total_label.config(text=str(self.detection_count))
        
        # Actualizar LED de detección si el sistema está corriendo
        if self.system_running:
            self.update_led("Sensor", "#C33B80", "SENSOR ACTIVO")
    
    def reset_detection_indicator(self):
        """Regresa el indicador de detección a estado normal"""
        self.detection_indicator.config(text="NO DETECTADO", bg="#D691B4", fg="#F8EAF2")
    
    def accumulate_realtime_count(self, color):
        """Acumula conteo en tiempo real (acumulativo)"""
        if color in self.realtime_counts:
            self.realtime_counts[color] += 1
        else:
            self.realtime_counts[color] = 1
        
        # Contar siempre (sin verificar tiempo)
        if color in self.box_count:
            self.box_count[color] += 1
            self.total_count += 1
            self.update_counters()
            self.update_color_display(color)
            self.log_event("Conteo", f"Caja {color} contada (Total: {self.total_count})")
    
    def start_realtime_timer(self):
        """Inicia el timer para actualizar contadores en tiempo real cada 1 segundo"""
        self.root.after(100, self._update_realtime_counts)
    
    def _update_realtime_counts(self):
        """Actualiza contadores en tiempo real SIN resetearlos"""
        try:
            # Actualizar etiquetas de tiempo real con valores acumulados
            self.detection_realtime_label.config(text=str(self.realtime_detections))
            
            for color in ["ROJO", "VERDE", "AZUL", "OTRO"]:
                count = self.realtime_counts.get(color, 0)
                self.realtime_labels[color].config(text=str(count))
            
            # NO resetear conteos - mantener acumulado
            # Los valores se mantienen acumulados hasta que se reseteen manualmente
            
            # Programar próxima actualización
            self.root.after(1000, self._update_realtime_counts)
            
        except Exception as e:
            self.log_event("Errores", f"Error actualizando contadores tiempo real: {str(e)}")
            self.root.after(1000, self._update_realtime_counts)
    
    def process_json_data(self, json_data):
        msg_type = json_data.get("type", "")
        
        if msg_type == "init":
            stm32_status = json_data.get("stm32", 0)
            speed = json_data.get("speed", 75)
            status = json_data.get("status", 0)
            detections = json_data.get("detections", 0)
            
            self.stm32_connected = stm32_status == 1
            self.conveyor_speed = speed
            self.esp_status = status
            self.detection_count = detections
            
            self.update_stm32_indicator()
            self.detection_total_label.config(text=str(self.detection_count))
            
            self.log_event("Comunicación", f"ESP32: Inicializado - STM32: {'Conectado' if stm32_status else 'Desconectado'}")
            self.update_info_text(f"ESP32 inicializado\nSTM32: {'Conectado' if stm32_status else 'Desconectado'}\n")
            
        elif msg_type == "data":
            red = json_data.get("red", 0)
            green = json_data.get("green", 0)
            blue = json_data.get("blue", 0)
            other = json_data.get("other", 0)
            total = json_data.get("total", 0)
            last_color = json_data.get("color", "NINGUNO")
            detections = json_data.get("detections", 0)
            
            # Usar los valores directamente del ESP32
            self.box_count["ROJO"] = red
            self.box_count["VERDE"] = green
            self.box_count["AZUL"] = blue
            self.box_count["OTRO"] = other
            self.total_count = total
            self.detection_count = detections
            
            self.update_counters()
            self.update_color_display(last_color)
            self.detection_total_label.config(text=str(self.detection_count))
            
            # Actualizar contadores en tiempo real con los valores acumulados
            self.realtime_counts["ROJO"] = red
            self.realtime_counts["VERDE"] = green
            self.realtime_counts["AZUL"] = blue
            self.realtime_counts["OTRO"] = other
            self.realtime_detections = detections
            
            # Actualizar etiquetas de tiempo real
            self._update_realtime_display()
            
        elif msg_type == "update":
            red = json_data.get("red", 0)
            green = json_data.get("green", 0)
            blue = json_data.get("blue", 0)
            other = json_data.get("other", 0)
            total = json_data.get("total", 0)
            last_color = json_data.get("last_color", "NINGUNO")
            speed = json_data.get("speed", 75)
            status = json_data.get("status", 0)
            detections = json_data.get("detections", 0)
            
            # Usar los valores directamente del ESP32
            self.box_count["ROJO"] = red
            self.box_count["VERDE"] = green
            self.box_count["AZUL"] = blue
            self.box_count["OTRO"] = other
            self.total_count = total
            self.conveyor_speed = speed
            self.esp_status = status
            self.detection_count = detections
            
            self.update_counters()
            self.update_color_display(last_color)
            self.detection_total_label.config(text=str(self.detection_count))
            
            # Actualizar contadores en tiempo real
            self.realtime_counts["ROJO"] = red
            self.realtime_counts["VERDE"] = green
            self.realtime_counts["AZUL"] = blue
            self.realtime_counts["OTRO"] = other
            self.realtime_detections = detections
            
            # Actualizar etiquetas de tiempo real
            self._update_realtime_display()
            
            if status == 1:
                self.update_led("Cinta", "#C33B80", "CINTA EN MOVIMIENTO")
                self.update_led("Sensor", "#C33B80", "SENSOR ACTIVO")
                self.update_led("Clasificación", "#C33B80", "CLASIFICACIÓN ACTIVA")
            elif status == 0:
                self.update_led("Cinta", "#D691B4", "CINTA DETENIDA")
                self.update_led("Sensor", "#D691B4", "SENSOR INACTIVO")
                self.update_led("Clasificación", "#D691B4", "CLASIFICACIÓN INACTIVA")
            
        elif msg_type == "status":
            speed = json_data.get("speed", 75)
            stm32 = json_data.get("stm32", 0)
            detections = json_data.get("detections", 0)
            
            self.conveyor_speed = speed
            self.stm32_connected = stm32 == 1
            self.detection_count = detections
            
            self.update_stm32_indicator()
            self.detection_total_label.config(text=str(self.detection_count))
            
        elif msg_type == "ok":
            cmd = json_data.get("cmd", "")
            if cmd == "start":
                self.system_running = True
                self.start_button.config(state="disabled", bg="#812E58")
                self.stop_button.config(state="normal", bg="#C33B80")
                self.update_led("Sensor", "#C33B80", "SENSOR ACTIVO")
                self.log_event("Sistema", "Sistema iniciado")
                self.update_info_text("Sistema iniciado\n")
            elif cmd == "stop":
                self.system_running = False
                self.start_button.config(state="normal", bg="#D691B4")
                self.stop_button.config(state="disabled", bg="#D691B4")
                self.update_led("Sensor", "#D691B4", "SENSOR INACTIVO")
                self.log_event("Sistema", "Sistema detenido")
                self.update_info_text("Sistema detenido\n")
            elif cmd == "reset":
                # Resetear contadores locales
                for color in self.box_count:
                    self.box_count[color] = 0
                self.total_count = 0
                self.detection_count = 0
                
                # Resetear contadores en tiempo real también
                self.realtime_counts.clear()
                self.realtime_detections = 0
                
                self.update_counters()
                self.update_color_display("NINGUNO")
                self.detection_total_label.config(text="0")
                self._update_realtime_display()  # Actualizar display de tiempo real
                self.log_event("Sistema", "Contadores reseteados")
                self.update_info_text("Contadores reseteados\n")
                
        elif msg_type == "alert":
            msg = json_data.get("msg", "")
            self.log_event("Alerta", msg)
            self.update_alarm_text(f"{msg}\n")
            
        elif msg_type == "ping_sent":
            self.log_event("Comunicación", "Ping enviado a STM32")
            
        elif msg_type == "error":
            error_msg = json_data.get("msg", "Error desconocido")
            self.log_event("Errores", f"Error: {error_msg}")
            self.update_alarm_text(f"Error: {error_msg}\n")
    
    def _update_realtime_display(self):
        """Actualiza las etiquetas de tiempo real inmediatamente"""
        self.detection_realtime_label.config(text=str(self.realtime_detections))
        for color in ["ROJO", "VERDE", "AZUL", "OTRO"]:
            count = self.realtime_counts.get(color, 0)
            self.realtime_labels[color].config(text=str(count))
    
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
    
    def get_status(self):
        if self.connected:
            self.send_command("GET_STATUS")
    
    def ping_stm32(self):
        if self.connected:
            self.send_command("PING_STM32")
    
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
    
    def reset_counters(self):
        if self.connected:
            self.send_command("RESET_COUNTERS")
        else:
            # Reset local
            for color in self.box_count:
                self.box_count[color] = 0
            self.total_count = 0
            self.detection_count = 0
            
            # Resetear contadores en tiempo real también
            self.realtime_counts.clear()
            self.realtime_detections = 0
            
            self.update_counters()
            self.update_color_display("NINGUNO")
            self.detection_total_label.config(text="0")
            self._update_realtime_display()  # Actualizar display de tiempo real
            self.detection_indicator.config(text="NO DETECTADO", bg="#D691B4")
            self.log_event("Sistema", "Contadores y detecciones reseteados localmente")
    
    # ========== ACTUALIZACIÓN AUTOMÁTICA ==========
    
    def start_auto_update(self):
        if self.connected and self.auto_update_var.get():
            try:
                interval = int(self.interval_entry.get())
            except ValueError:
                interval = 1000
                
            interval = max(100, interval)  # Mínimo 100ms
            self.data_timer = self.root.after(interval, self._auto_update)
    
    def _auto_update(self):
        if self.connected and self.auto_update_var.get():
            self.request_data()
            try:
                interval = int(self.interval_entry.get())
            except ValueError:
                interval = 1000
                
            interval = max(100, interval)
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
        self.detection_total_label.config(text=str(self.detection_count))
    
    def update_color_display(self, color):
        self.current_color = color
        self.color_display.config(text=color)
        
        color_map = {
            "ROJO": "#C33B80",
            "VERDE": "#C33B80", 
            "AZUL": "#C33B80",
            "OTRO": "#C33B80",
            "NINGUNO": "#D691B4"
        }
        
        bg_color = color_map.get(color, "#D691B4")
        fg_color = "#F8EAF2"
        
        self.color_display.config(bg=bg_color, fg=fg_color)
        
        if color != "NINGUNO":
            self.log_event("Detecciones", f"Color detectado: {color}")
    
    def update_stm32_indicator(self):
        if self.stm32_connected:
            self.stm32_indicator.config(text="CONECTADO", fg="#C33B80")
        else:
            self.stm32_indicator.config(text="DESCONECTADO", fg="#C33B80")
    
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
                "auto_update": self.auto_update_var.get(),
                "update_interval": self.interval_entry.get()
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
            self.ip_entry.insert(0, config.get("tcp_host", "192.168.4.1"))
            
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, str(config.get("tcp_port", 8080)))
            
            self.interval_entry.delete(0, tk.END)
            self.interval_entry.insert(0, str(config.get("update_interval", "1000")))
            
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
    system_menu.add_command(label="Obtener Estado", command=app.get_status)
    
    root.mainloop()

if __name__ == "__main__":
    main()