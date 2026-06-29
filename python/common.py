# Common functionality
from cobs import cobs
import aiocoap
import json # To handle parameter file directly
import socket
import time
import parameters_pb2 as params

UDP_IP = "127.0.0.1"
UDP_VESSEL_PORT = 55501
UDP_ROV_DRY_PORT = 55502
UDP_ROV_WET_PORT = 55522
UDP_REMOTE_PORT = 55503
# UDP_PORTS = {"vessel":UDP_VESSEL_PORT, "rov":UDP_ROV_PORT, "remote":UDP_REMOTE_PORT}

# Fields in INTERFACES definition are:
# 0 type of interface, one of
#  "udp" - UDP
#  "serial" - serial over physical serial port
#  "serial_over_udp" - serial formatted message sent over UDP for simulation or to UDP serial port server
# 1 string representation of either IP address (for udp or serial_over_udp), or serial port name for serial
# 2 number representing UDP port number (for udp or serial_over_udp), or baud rate for serial
INTERFACES = {
    # "vessel":["udp", UDP_IP, UDP_VESSEL_PORT],
    # "vessel":["serial", "COM8", 19200],
    "vessel":["serial_over_udp", UDP_IP, UDP_VESSEL_PORT],
    # "rov_dry":["udp", UDP_IP, UDP_ROV_DRY_PORT],
    # "rov_dry":["serial", "COM9", 19200],
    "rov_dry":["serial_over_udp", UDP_IP, UDP_ROV_DRY_PORT],
    "rov_wet":["udp", UDP_IP, UDP_ROV_WET_PORT],
    "remote":["udp", UDP_IP, UDP_REMOTE_PORT],
    }
PORTS = ["ZERO", "vessel", "rov_dry", "rov_wet", "remote"]
WIRELESS_LATENCY = 0.1  # Simulated latency in seconds

with open('parameters.json') as json_file:  # Provide wireless_parameter_specification dictionary for devices
    full_spec = json.load(json_file)["all"]
    # load the parameters into dictionary keyed by ID
    spec_by_id = {}
    spec_by_name = {}
    for param in full_spec:
        spec_by_id[param["id"]] = param
        spec_by_name[param["name"]] = param

def get_specification(key):
    if isinstance(key, int):
        print(f"common ID:{key}: Spec:{spec_by_id[key]}")
        return spec_by_id[key]
    else:
        return spec_by_name[key]


def report(proto, description=""):
    """ Display debug information about the message"""
    tx_bytes = proto.SerializeToString()
    print(f"{description} {str(tx_bytes)} ({len(tx_bytes)} bytes)")


def sendMessage(proto, portname, port_handle=None):
    """ Send the message to a specified interface"""
    time.sleep(WIRELESS_LATENCY)
    if INTERFACES[portname][0] == "udp":
        buffer = proto.SerializeToString()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.sendto(buffer, (INTERFACES[portname][1], INTERFACES[portname][2]))
        print(f"Sent UDP message to {portname} ({INTERFACES[portname][1]}:{INTERFACES[portname][2]}) - {len(buffer)} bytes")
    elif INTERFACES[portname][0] == "serial":
        proto_bytes = proto.SerializeToString()
        proto_bytes += bytes([0x43, 0x52])  # CRC placeholder "CR"- TODO implement CRC
        print("TODO append real CRC to buffer")
        buffer = bytes([0x00])
        buffer += cobs.encode(proto_bytes)
        buffer += bytes([0x00])  # COBS delimiter
        port_handle.write(buffer)
        print(f"Sent serial message to {portname} ({INTERFACES[portname][1]}) - {len(buffer)} bytes")
    elif INTERFACES[portname][0] == "serial_over_udp":
        proto_bytes = proto.SerializeToString()
        proto_bytes += bytes([0x43, 0x52])  # CRC placeholder "CR"- TODO implement CRC
        print("TODO append real CRC to buffer")
        buffer = bytes([0x00])
        buffer += cobs.encode(proto_bytes)
        buffer += bytes([0x00])  # COBS delimiter
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.sendto(buffer, (INTERFACES[portname][1], INTERFACES[portname][2]))
        print(f"Sent serial format message over UDP to {portname} ({INTERFACES[portname][1]}:{INTERFACES[portname][2]}) - {len(buffer)} bytes")
    else:
        print(f"Interface definition not supported for {portname} - {INTERFACES[portname]}")


def getUdpInput(portname):
    print(f'Getting UDP for {portname}')
    sock = socket.socket(socket.AF_INET, # Internet
            socket.SOCK_DGRAM) # UDP
    sock.bind((INTERFACES[portname][1], INTERFACES[portname][2]))
    sock.setblocking(0)
    return sock


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    """ Calculate the CRC16-CCITT checksum for the given data with CRC specifications:
        polynomial 0x1021, initial value 0xFFFF, no final XOR, and no reflection.
        Verified against https://www.codertools.net/tools/crc.php     
    """
    poly = 0x1021
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def get_udp_message_bytes(code, protobuf, mid, mtype):
    """ Create a UDP message with the given code, protobuf, and message ID
        as a CoAP message byte stream, with the provided parameters
    """
    message = aiocoap.Message(code=code, payload=protobuf)
    message.mid = mid
    message.mtype = mtype
    return message.encode()


def get_serial_message_bytes(code, protobuf, mid, mtype):
    """ Create a serial message with the given code, protobuf, and message ID
        by wrapping the base CoAP message with checksum, COBS encoding, and null delimiters
    """
    message_bytes = get_udp_message_bytes(code, protobuf, mid, mtype)
    serial_crc = crc16_ccitt(message_bytes).to_bytes(2, "big")
    serial_message = bytes([0x00]) + cobs.encode(message_bytes + serial_crc) + bytes([0x00])
    return serial_message


def coap_message_from_udp_bytes(message_bytes):
    """ Extract the CoAP message from a UDP message"""
    message = aiocoap.Message.decode(message_bytes)
    return message


def coap_message_from_serial_bytes(serial_message):
    """ Extract the CoAP message from a serial message
        removing serial-specific framing and using 
        coap_message_from_udp_bytes to decode the CoAP message
    """
    # Remove any leading and trailing null COBS delimiter(s)
    while serial_message.startswith(b'\x00') and len(serial_message) > 1:
        serial_message = serial_message[1:]
    while serial_message.endswith(b'\x00') and len(serial_message) > 1:
        serial_message = serial_message[:-1]

    if len(serial_message) > 3: # data + CRC
        cobs_decoded = cobs.decode(serial_message)
        message_bytes = cobs_decoded[:-2]  # Remove CRC
        crc_received = int.from_bytes(cobs_decoded[-2:], "big")
        crc_calculated = crc16_ccitt(message_bytes)
        if crc_received == crc_calculated:
            return coap_message_from_udp_bytes(message_bytes)
        else:
            raise ValueError("Serial CRC mismatch")
    else:
        raise ValueError("Serial message too short")