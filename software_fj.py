from abc import ABC, abstractmethod
from builtins import Exception, isinstance, print, str, super
from typing import List
import datetime
import os
import re


# ==========================================
# 1. EXCEPCIONES PERSONALIZADAS
# ==========================================
class SoftwareFJError(Exception):
    """Excepción base para todos los errores del sistema Software FJ."""
    pass


class DatosInvalidosError(SoftwareFJError):
    """Se lanza cuando los parámetros ingresados son nulos, vacíos o tienen formato incorrecto."""
    pass


class ServicioNoDisponibleError(SoftwareFJError):
    """Se lanza cuando se intenta reservar o usar un servicio inactivo o sin cupo."""
    pass


class OperacionNoPermitidaError(SoftwareFJError):
    """Se lanza cuando se intenta una transición de estado inválida."""
    pass


class CalculoInconsistenteError(SoftwareFJError):
    """Se lanza cuando ocurre un fallo aritmético o valores negativos en costos."""
    pass


class EntidadNoEncontradaError(SoftwareFJError):
    """Se lanza cuando se busca un cliente, servicio o reserva inexistente en las listas internas."""
    pass


# ==========================================
# 2. MANEJADOR DE ARCHIVO DE LOGS
# ==========================================
class SistemaLogger:
    """Gestiona el registro persistente de eventos y excepciones en un archivo de texto."""

    def __init__(self, ruta_archivo: str = "registro_eventos.log"):
        self._ruta_archivo = ruta_archivo

    def registrar_evento(self, nivel: str, mensaje: str) -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{timestamp}] [{nivel.upper()}] {mensaje}\n"
        archivo = None
        try:
            archivo = open(self._ruta_archivo, "a", encoding="utf-8")
            archivo.write(linea)
        except IOError as e:
            print(f"[ALERTA CRÍTICA DE LOG] No se pudo escribir en disco: {e}")
        finally:
            if archivo is not None:
                archivo.close()

    def registrar_error(self, error: Exception, contexto: str = "") -> None:
        detalle_causa = ""
        if error.__cause__:
            detalle_causa = f" | Causado por: {type(error.__cause__).__name__}: {error.__cause__}"

        mensaje = (
            f"Contexto: {contexto} | Excepción: {type(error).__name__} -> {error}{detalle_causa}"
        )
        self.registrar_evento("ERROR", mensaje)


# ==========================================
# 3. CLASE ABSTRACTA BASE DEL SISTEMA
# ==========================================
class EntidadSistema(ABC):
    """Clase abstracta que representa cualquier entidad identificable de Software FJ."""

    def __init__(self, id_entidad: str):
        if not id_entidad or not isinstance(id_entidad, str) or not id_entidad.strip():
            raise DatosInvalidosError("El ID de la entidad no puede estar vacío.")
        self._id = id_entidad.strip()

    @property
    def id(self) -> str:
        return self._id

    @abstractmethod
    def validar_integridad(self) -> bool:
        """Verifica que todos los atributos de la entidad cumplan las reglas del negocio."""
        pass

    @abstractmethod
    def obtener_resumen(self) -> str:
        """Devuelve una representación legible de la entidad."""
        pass


# ==========================================
# 4. CLASE CLIENTE (ENCAPSULACIÓN ESTRICTA)
# ==========================================
class Cliente(EntidadSistema):
    """Representa un cliente de Software FJ con validación estricta de datos personales."""

    def __init__(self, id_cliente: str, nombre: str, email: str, telefono: str):
        super().__init__(id_cliente)
        self.nombre = nombre
        self.email = email
        self.telefono = telefono
        self.validar_integridad()

    @property
    def nombre(self) -> str:
        return self._nombre

    @nombre.setter
    def nombre(self, valor: str):
        if not valor or not isinstance(valor, str) or len(valor.strip()) < 3:
            raise DatosInvalidosError("El nombre del cliente debe tener al menos 3 caracteres.")
        self._nombre = valor.strip()

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, valor: str):
        patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not valor or not isinstance(valor, str) or not re.match(patron, valor.strip()):
            raise DatosInvalidosError(f"Correo electrónico inválido: '{valor}'.")
        self._email = valor.strip()

    @property
    def telefono(self) -> str:
        return self._telefono

    @telefono.setter
    def telefono(self, valor: str):
        if not valor or not isinstance(valor, str) or not valor.strip().isdigit() or len(valor.strip()) < 7:
            raise DatosInvalidosError(f"Teléfono inválido (debe contener mínimo 7 dígitos): '{valor}'.")
        self._telefono = valor.strip()

    def validar_integridad(self) -> bool:
        return bool(self._id and self._nombre and self._email and self._telefono)

    def obtener_resumen(self) -> str:
        return f"Cliente [{self._id}]: {self._nombre} | Email: {self._email} | Tel: {self._telefono}"


# ==========================================
# 5. CLASE ABSTRACTA SERVICIO Y DERIVADAS
# ==========================================
class Servicio(EntidadSistema, ABC):
    """Clase abstracta para los servicios ofrecidos por Software FJ."""

    def __init__(self, id_servicio: str, nombre: str, tarifa_base: float, disponible: bool = True):
        super().__init__(id_servicio)
        if not nombre or not isinstance(nombre, str):
            raise DatosInvalidosError("El nombre del servicio es obligatorio.")
        try:
            tarifa_num = float(tarifa_base)
        except (ValueError, TypeError) as e:
            raise DatosInvalidosError(f"La tarifa base '{tarifa_base}' debe ser numérica.") from e

        if tarifa_num <= 0:
            raise DatosInvalidosError("La tarifa base debe ser mayor a cero.")

        self._nombre = nombre.strip()
        self._tarifa_base = tarifa_num
        self._disponible = bool(disponible)

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def tarifa_base(self) -> float:
        return self._tarifa_base

    @property
    def disponible(self) -> bool:
        return self._disponible

    @disponible.setter
    def disponible(self, estado: bool):
        self._disponible = bool(estado)

    @abstractmethod
    def calcular_tarifa_base(self, duracion_horas: float) -> float:
        pass

    @abstractmethod
    def describir_servicio(self) -> str:
        pass

    # MÉTODO SOBRECARGADO (mediante parámetros opcionales y validación dinámica)
    def calcular_costo(
        self,
        duracion_horas: float,
        impuesto_pct: float = 0.0,
        descuento_pct: float = 0.0,
        recargo_fijo: float = 0.0,
    ) -> float:
        if duracion_horas <= 0:
            raise DatosInvalidosError("La duración debe ser mayor a 0 horas.")
        if impuesto_pct < 0 or descuento_pct < 0 or descuento_pct > 100 or recargo_fijo < 0:
            raise CalculoInconsistenteError("Porcentajes de impuesto/descuento o recargos fuera de rango válido.")

        try:
            subtotal = self.calcular_tarifa_base(duracion_horas)
            monto_descuento = subtotal * (descuento_pct / 100.0)
            base_imponible = (subtotal - monto_descuento) + recargo_fijo
            monto_impuesto = base_imponible * (impuesto_pct / 100.0)
            total = round(base_imponible + monto_impuesto, 2)

            if total < 0:
                raise CalculoInconsistenteError("El cálculo arrojó un total negativo.")
            return total
        except Exception as e:
            if isinstance(e, (DatosInvalidosError, CalculoInconsistenteError)):
                raise
            raise CalculoInconsistenteError("Error inesperado durante el cálculo financiero del servicio.") from e

    def validar_integridad(self) -> bool:
        return self._tarifa_base > 0 and len(self._nombre) > 0

    def obtener_resumen(self) -> str:
        estado = "Disponible" if self._disponible else "No Disponible"
        return f"Servicio [{self._id}] {self._nombre} (${self._tarifa_base}/h) - {estado}"


class ReservaSala(Servicio):
    """Servicio especializado para alquiler de salas de reuniones o auditorios."""

    def __init__(self, id_servicio: str, nombre: str, tarifa_base: float, capacidad: int, tiene_videoconferencia: bool):
        super().__init__(id_servicio, nombre, tarifa_base)
        if not isinstance(capacidad, int) or capacidad <= 0:
            raise DatosInvalidosError("La capacidad de la sala debe ser un entero positivo.")
        self._capacidad = capacidad
        self._tiene_videoconferencia = bool(tiene_videoconferencia)

    def calcular_tarifa_base(self, duracion_horas: float) -> float:
        costo = self._tarifa_base * duracion_horas
        if self._tiene_videoconferencia:
            costo *= 1.15
        return costo

    def describir_servicio(self) -> str:
        vc = "con sistema de videoconferencia" if self._tiene_videoconferencia else "estándar"
        return f"Sala '{self._nombre}' (Capacidad: {self._capacidad} personas, {vc})."


class AlquilerEquipo(Servicio):
    """Servicio especializado para alquiler de hardware y estaciones de trabajo."""

    def __init__(self, id_servicio: str, nombre: str, tarifa_base: float, categoria_equipo: str, requiere_deposito: bool):
        super().__init__(id_servicio, nombre, tarifa_base)
        if not categoria_equipo or not isinstance(categoria_equipo, str):
            raise DatosInvalidosError("La categoría del equipo es obligatoria.")
        self._categoria = categoria_equipo.strip()
        self._requiere_deposito = bool(requiere_deposito)

    def calcular_tarifa_base(self, duracion_horas: float) -> float:
        costo = self._tarifa_base * duracion_horas
        if self._requiere_deposito:
            costo += 25.0
        return costo

    def describir_servicio(self) -> str:
        dep = "Requiere depósito de garantía" if self._requiere_deposito else "Sin depósito"
        return f"Equipo [{self._categoria}]: {self._nombre} ({dep})."


class AsesoriaEspecializada(Servicio):
    """Servicio especializado de consultoría técnica o arquitectura de software."""

    def __init__(self, id_servicio: str, nombre: str, tarifa_base: float, area_especialidad: str, nivel_senior: bool):
        super().__init__(id_servicio, nombre, tarifa_base)
        if not area_especialidad or not isinstance(area_especialidad, str):
            raise DatosInvalidosError("El área de especialidad es obligatoria.")
        self._especialidad = area_especialidad.strip()
        self._nivel_senior = bool(nivel_senior)

    def calcular_tarifa_base(self, duracion_horas: float) -> float:
        multiplicador = 1.4 if self._nivel_senior else 1.0
        return (self._tarifa_base * multiplicador) * duracion_horas

    def describir_servicio(self) -> str:
        nivel = "Consultor Senior" if self._nivel_senior else "Consultor Semi-Senior"
        return f"Asesoría en {self._especialidad} ({nivel}): {self._nombre}."


# ==========================================
# 6. CLASE RESERVA
# ==========================================
class Reserva(EntidadSistema):
    """Integra un Cliente, un Servicio y gestiona el ciclo de vida de la reserva."""

    ESTADOS_VALIDOS = ("PENDIENTE", "CONFIRMADA", "CANCELADA", "COMPLETADA")

    def __init__(self, id_reserva: str, cliente: Cliente, servicio: Servicio, duracion_horas: float):
        super().__init__(id_reserva)
        if not isinstance(cliente, Cliente):
            raise DatosInvalidosError("Se requiere una instancia válida de Cliente.")
        if not isinstance(servicio, Servicio):
            raise DatosInvalidosError("Se requiere una instancia válida de Servicio.")
        if not servicio.disponible:
            raise ServicioNoDisponibleError(f"El servicio '{servicio.nombre}' no está disponible actualmente.")
        if duracion_horas <= 0:
            raise DatosInvalidosError("La duración de la reserva debe ser mayor a cero.")

        self._cliente = cliente
        self._servicio = servicio
        self._duracion_horas = float(duracion_horas)
        self._estado = "PENDIENTE"
        self._costo_final = 0.0

    @property
    def estado(self) -> str:
        return self._estado

    @property
    def costo_final(self) -> float:
        return self._costo_final

    def confirmar(self, impuesto_pct: float = 19.0, descuento_pct: float = 0.0) -> float:
        if self._estado != "PENDIENTE":
            raise OperacionNoPermitidaError(
                f"No se puede confirmar la reserva '{self._id}' porque su estado actual es '{self._estado}'."
            )
        if not self._servicio.disponible:
            raise ServicioNoDisponibleError(
                f"El servicio '{self._servicio.nombre}' dejó de estar disponible antes de confirmar."
            )

        self._costo_final = self._servicio.calcular_costo(
            self._duracion_horas, impuesto_pct=impuesto_pct, descuento_pct=descuento_pct
        )
        self._estado = "CONFIRMADA"
        self._servicio.disponible = False
        return self._costo_final

    def cancelar(self) -> None:
        if self._estado in ("CANCELADA", "COMPLETADA"):
            raise OperacionNoPermitidaError(
                f"No se puede cancelar la reserva '{self._id}' en estado '{self._estado}'."
            )
        self._estado = "CANCELADA"
        self._servicio.disponible = True

    def procesar_finalizacion(self) -> None:
        if self._estado != "CONFIRMADA":
            raise OperacionNoPermitidaError(
                f"Solo se pueden completar reservas CONFIRMADAS (estado actual: '{self._estado}')."
            )
        self._estado = "COMPLETADA"
        self._servicio.disponible = True

    def validar_integridad(self) -> bool:
        return self._estado in self.ESTADOS_VALIDOS and self._duracion_horas > 0

    def obtener_resumen(self) -> str:
        return (
            f"Reserva [{self._id}] | Estado: {self._estado} | Cliente: {self._cliente.nombre} | "
            f"Servicio: {self._servicio.nombre} ({self._duracion_horas}h) | Total: ${self._costo_final:.2f}"
        )


# ==========================================
# 7. GESTOR EN MEMORIA (SIN BASE DE DATOS)
# ==========================================
class GestorSoftwareFJ:
    """Controlador central que gestiona colecciones en memoria sin base de datos."""

    def __init__(self, logger: SistemaLogger):
        self._clientes: List[Cliente] = []
        self._servicios: List[Servicio] = []
        self._reservas: List[Reserva] = []
        self._logger = logger

    def registrar_cliente(self, cliente: Cliente) -> bool:
        try:
            if any(c.id == cliente.id for c in self._clientes):
                raise DatosInvalidosError(f"Ya existe un cliente registrado con el ID '{cliente.id}'.")
            self._clientes.append(cliente)
        except SoftwareFJError as e:
            self._logger.registrar_error(e, contexto=f"Registro de cliente ID={getattr(cliente, 'id', 'Desconocido')}")
            print(f"[ERROR CONTROLADO] {e}")
            return False
        else:
            self._logger.registrar_evento("INFO", f"Cliente registrado exitosamente: {cliente.obtener_resumen()}")
            print(f"[OK] {cliente.obtener_resumen()}")
            return True

    def registrar_servicio(self, servicio: Servicio) -> bool:
        try:
            if any(s.id == servicio.id for s in self._servicios):
                raise DatosInvalidosError(f"Ya existe un servicio registrado con el ID '{servicio.id}'.")
            self._servicios.append(servicio)
        except SoftwareFJError as e:
            self._logger.registrar_error(e, contexto=f"Registro de servicio ID={getattr(servicio, 'id', 'Desconocido')}")
            print(f"[ERROR CONTROLADO] {e}")
            return False
        else:
            self._logger.registrar_evento("INFO", f"Servicio creado: {servicio.describir_servicio()}")
            print(f"[OK] Servicio registrado -> {servicio.describir_servicio()}")
            return True

    def buscar_cliente(self, id_cliente: str) -> Cliente:
        for c in self._clientes:
            if c.id == id_cliente:
                return c
        raise EntidadNoEncontradaError(f"No se encontró el cliente con ID '{id_cliente}'.")

    def buscar_servicio(self, id_servicio: str) -> Servicio:
        for s in self._servicios:
            if s.id == id_servicio:
                return s
        raise EntidadNoEncontradaError(f"No se encontró el servicio con ID '{id_servicio}'.")

    def crear_y_confirmar_reserva(
        self,
        id_reserva: str,
        id_cliente: str,
        id_servicio: str,
        duracion_horas: float,
        impuesto_pct: float = 19.0,
        descuento_pct: float = 0.0,
    ) -> bool:
        try:
            cliente = self.buscar_cliente(id_cliente)
            servicio = self.buscar_servicio(id_servicio)

            if any(r.id == id_reserva for r in self._reservas):
                raise DatosInvalidosError(f"El ID de reserva '{id_reserva}' ya está en uso.")

            nueva_reserva = Reserva(id_reserva, cliente, servicio, duracion_horas)
            nueva_reserva.confirmar(impuesto_pct=impuesto_pct, descuento_pct=descuento_pct)
            self._reservas.append(nueva_reserva)
        except SoftwareFJError as e:
            self._logger.registrar_error(
                e, contexto=f"Creación/Confirmación de Reserva {id_reserva} (Cliente={id_cliente}, Servicio={id_servicio})"
            )
            print(f"[ERROR CONTROLADO EN RESERVA] {e}")
            return False
        else:
            self._logger.registrar_evento("INFO", f"Reserva confirmada: {nueva_reserva.obtener_resumen()}")
            print(f"[OK] {nueva_reserva.obtener_resumen()}")
            return True
        finally:
            self._logger.registrar_evento("AUDIT", f"Finalizado intento de transacción para Reserva '{id_reserva}'.")

    def cancelar_reserva(self, id_reserva: str) -> bool:
        try:
            reserva = next((r for r in self._reservas if r.id == id_reserva), None)
            if reserva is None:
                raise EntidadNoEncontradaError(f"La reserva '{id_reserva}' no existe.")
            reserva.cancelar()
        except SoftwareFJError as e:
            self._logger.registrar_error(e, contexto=f"Cancelación de reserva {id_reserva}")
            print(f"[ERROR CONTROLADO] {e}")
            return False
        else:
            self._logger.registrar_evento("INFO", f"Reserva '{id_reserva}' cancelada y servicio liberado.")
            print(f"[OK] Reserva '{id_reserva}' cancelada exitosamente.")
            return True

    def completar_reserva(self, id_reserva: str) -> bool:
        try:
            reserva = next((r for r in self._reservas if r.id == id_reserva), None)
            if reserva is None:
                raise EntidadNoEncontradaError(f"La reserva '{id_reserva}' no existe.")
            reserva.procesar_finalizacion()
        except SoftwareFJError as e:
            self._logger.registrar_error(e, contexto=f"Finalización de reserva {id_reserva}")
            print(f"[ERROR CONTROLADO] {e}")
            return False
        else:
            self._logger.registrar_evento("INFO", f"Reserva '{id_reserva}' completada satisfactoriamente.")
            print(f"[OK] Reserva '{id_reserva}' marcada como COMPLETADA.")
            return True

    def mostrar_reporte_estado(self) -> None:
        print("\n" + "=" * 65)
        print("REPORTE GENERAL DEL SISTEMA - SOFTWARE FJ (EN MEMORIA)")
        print("=" * 65)
        print(f"Total Clientes: {len(self._clientes)} | Total Servicios: {len(self._servicios)} | Total Reservas: {len(self._reservas)}")
        print("\n--- Estado de Servicios ---")
        for s in self._servicios:
            print("  •", s.obtener_resumen())
        print("\n--- Estado de Reservas ---")
        for r in self._reservas:
            print("  •", r.obtener_resumen())
        print("=" * 65 + "\n")


# ==========================================
# 8. EJECUCIÓN DE LAS 12 OPERACIONES
# ==========================================
def ejecutar_simulacion():
    # Guarda registro_eventos.log exactamente en la misma carpeta donde está este archivo .py
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_log = os.path.join(directorio_actual, "registro_eventos.log")

    logger = SistemaLogger(ruta_log)
    logger.registrar_evento("SYSTEM", "=== INICIO DE EJECUCIÓN DEL SISTEMA SOFTWARE FJ ===")
    gestor = GestorSoftwareFJ(logger)

    print("=== INICIANDO SIMULACIÓN DE OPERACIONES EN SOFTWARE FJ ===\n")

    # 1. Cliente válido
    print("1. Registrando cliente válido (C01)...")
    try:
        c1 = Cliente("C01", "Laura Gómez", "laura.gomez@empresa.com", "3104567890")
        gestor.registrar_cliente(c1)
    except SoftwareFJError as e:
        logger.registrar_error(e, "Instanciación C01")

    # 2. Cliente inválido (email mal formado)
    print("\n2. Intentando registrar cliente con correo inválido (C02)...")
    try:
        c2 = Cliente("C02", "Carlos Ruiz", "carlos.sin.arroba.com", "3001234567")
        gestor.registrar_cliente(c2)
    except SoftwareFJError as e:
        logger.registrar_error(e, "Instanciación C02")
        print(f"[EXCEPCIÓN CAPTURADA EN MAIN] {e}")

    # 3. Segundo cliente válido
    print("\n3. Registrando segundo cliente válido (C03)...")
    try:
        c3 = Cliente("C03", "Andrés Mendoza", "amendoza@techcorp.co", "3159876543")
        gestor.registrar_cliente(c3)
    except SoftwareFJError as e:
        logger.registrar_error(e, "Instanciación C03")

    # 4. Creación válida de 3 servicios especializados
    print("\n4. Creando servicios especializados válidos (S01, S02, S03)...")
    try:
        s1 = ReservaSala("S01", "Sala Innovación A", 100.0, capacidad=12, tiene_videoconferencia=True)
        s2 = AlquilerEquipo("S02", "Workstation Mac Studio M2", 45.0, categoria_equipo="Cómputo", requiere_deposito=True)
        s3 = AsesoriaEspecializada("S03", "Arquitectura Cloud AWS", 150.0, area_especialidad="Cloud", nivel_senior=True)
        gestor.registrar_servicio(s1)
        gestor.registrar_servicio(s2)
        gestor.registrar_servicio(s3)
    except SoftwareFJError as e:
        logger.registrar_error(e, "Creación servicios válidos")

    # 5. Creación incorrecta de servicio (encadenamiento de excepciones)
    print("\n5. Intentando crear servicio con tarifa inválida (S04)...")
    try:
        s_invalido = AlquilerEquipo("S04", "Servidor Rack", "CIEN_DOLARES", "Redes", False)
        gestor.registrar_servicio(s_invalido)
    except SoftwareFJError as e:
        logger.registrar_error(e, "Instanciación S04")
        print(f"[EXCEPCIÓN ENCADENADA CAPTURADA] {e} | Causa original: {type(e.__cause__).__name__}")

    # 6. Reserva exitosa 1
    print("\n6. Creando reserva exitosa R01 (Cliente C01 reserva Sala S01 por 3 horas)...")
    gestor.crear_y_confirmar_reserva("R01", "C01", "S01", duracion_horas=3, impuesto_pct=19.0)

    # 7. Reserva fallida (servicio ocupado)
    print("\n7. Intentando reservar servicio ocupado (Cliente C03 intenta reservar S01)...")
    gestor.crear_y_confirmar_reserva("R02", "C03", "S01", duracion_horas=2)

    # 8. Reserva exitosa 2 con sobrecarga de parámetros (Impuesto + Descuento)
    print("\n8. Creando reserva exitosa R03 con descuento empresarial del 10% (Cliente C03 -> Asesoría S03)...")
    gestor.crear_y_confirmar_reserva("R03", "C03", "S03", duracion_horas=4, impuesto_pct=19.0, descuento_pct=10.0)

    # 9. Reserva fallida por cálculo inconsistente
    print("\n9. Intentando crear reserva con descuento inválido del 150% (R04)...")
    gestor.crear_y_confirmar_reserva("R04", "C01", "S02", duracion_horas=2, impuesto_pct=19.0, descuento_pct=150.0)

    # 10. Finalización de reserva R01 y liberación de Sala S01
    print("\n10. Completando reserva R01 para liberar la Sala S01...")
    gestor.completar_reserva("R01")

    # 11. Operación no permitida (cancelar reserva ya completada)
    print("\n11. Intentando cancelar la reserva R01 que ya está COMPLETADA...")
    gestor.cancelar_reserva("R01")

    # 12. Nueva reserva exitosa sobre sala liberada
    print("\n12. Re-reservando la Sala S01 liberada para el cliente C03 (R05)...")
    gestor.crear_y_confirmar_reserva("R05", "C03", "S01", duracion_horas=2, impuesto_pct=19.0)

    gestor.mostrar_reporte_estado()
    logger.registrar_evento("SYSTEM", "=== FIN DE EJECUCIÓN SIN INTERRUPCIONES ===")
    print(f"Simulación finalizada. Archivo de logs guardado en:\n{ruta_log}")


if __name__ == "__main__":
    ejecutar_simulacion()
