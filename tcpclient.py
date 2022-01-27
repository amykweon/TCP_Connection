import socket
import struct
import threading
import array
import sys
import time

# created packet saved in global variable
packets = []
event_array = dict()
thread_array = dict()

sourceip = 0
sourceport = 0
ackport = 0
window = 0

dev_rtt = 0
estimated = 0.18
time_out = 0.18

def checksum(msg):
	if len(msg) % 2 != 0:
		msg += b'\0'
	res = sum(array.array("H", msg))
	res = (res >> 16) + (res & 0xffff)
	res += res >> 16
	return (~res) & 0xffff

def create_packet(seq, ack, fin, syn, msg):
	tcp_source = ackport
	tcp_dest = sourceport
	tcp_seq = seq
	tcp_ack_seq = ack
	tcp_doff = 5

	#tcp flags
	tcp_fin = fin
	if (syn):
		tcp_syn = 0
	else:
		tcp_syn = 1
	tcp_ack = 0
	tcp_check = 0
	tcp_window = window

	#tcp flags not used
	tcp_rst = 0
	tcp_psh = 0
	tcp_urg = 0
	tcp_urg_ptr = 0

	tcp_offset_res = (tcp_doff << 4) + 0
	tcp_flags = tcp_fin + (tcp_syn << 1) + (tcp_rst << 2) + (tcp_psh << 3) + (tcp_ack << 4) + (tcp_urg << 5)

	tcp_header = struct.pack('!HHLLBBHHH', tcp_source, tcp_dest, tcp_seq, tcp_ack_seq, tcp_offset_res, tcp_flags, tcp_window, tcp_check, tcp_urg_ptr)
	packet = tcp_header + msg
	tcp_check = checksum(packet)

	# update checksum to the header
	tcp_header = struct.pack('!HHLLBBH', tcp_source, tcp_dest, tcp_seq, tcp_ack_seq, tcp_offset_res, tcp_flags, tcp_window) + struct.pack('H', tcp_check) + struct.pack('!H', tcp_urg_ptr)
	packet = tcp_header + msg
	
	return packet

# update timer related global variables
def update_tcp_timer (sample_time):
	global dev_rtt
	global estimated
	global time_out

	dev_rtt = (1-0.125) * dev_rtt + 0.125 * abs(estimated-sample_time)
	estimated = (1-0.125) * estimated + 0.125 * sample_time
	time_out = estimated + 4 * dev_rtt

def sending_thread (ack_recv, next_index, sock):
	initial = 0
	while not ack_recv.is_set(): # retransmit when ACK is not received
		initial += 1
		start = time.time()
		
		sock.sendto(packets[next_index], (sourceip, sourceport))
		
		ack_recv.wait(time_out)
		end = time.time()
	
	# disregard retransmission timer; update timeout otherwise
	if (initial == 1):
		update_tcp_timer(end-start)

def client_main_thread(sock):
	ack_buffer = []
	send_base = 0
	next_index = 0
	s_window = window * 2 # prevent SR Dilemma

	while True:
		 # send if send_base changed; stop when last packet sending thread is created
		while (next_index - send_base < window and next_index <= len(packets) - 1):
			# create separate thread to send packets
			event_array[next_index % s_window] = threading.Event()
			thread_array[next_index % s_window] = threading.Thread(target=sending_thread, args=(event_array[next_index % s_window], next_index, sock))
			thread_array[next_index % s_window].start()
			next_index += 1
		
		# parse ACK packet and handle retransmission 
		ack = parse_ack(sock)
		event_array[ack % s_window].set()
		thread_array[ack % s_window].join()

		# save ACK received; update send_base accordingly
		ack_buffer.append(ack)
		ack_buffer.sort()
		for i in range(0, len(ack_buffer)):
			if (ack_buffer[i] == send_base):
				ack_buffer[i] = -1
				send_base += 1
		ack_buffer[:] = [x for x in ack_buffer if not x == -1]
		
		# if all packets transmitted, return
		if (send_base == len(packets)):
			return

def parse_ack (sock):
	ack = sock.recvfrom(20)
	header = struct.unpack('!HHLLBBHHH', ack[0])
	# translate ack to index used in tcpclient
	ack_num = header[3] // 576
	return ack_num - 1

if __name__ == '__main__':
	if (len(sys.argv) != 6):
		print("python3 tcpclient.py <file> <address of udpl> <udpl port number> <window size> <ack port number>")
		sys.exit()

	file = sys.argv[1]
	# define global variables
	sourceip = sys.argv[2]
	sourceport = int(sys.argv[3])
	window = (int(sys.argv[4])) // 596
	ackport = int(sys.argv[5])

	f = open(file, "rb")
	# packet size = 596
	msg = f.read(576)

	# for SYN flag
	count = 0
	# byte count for seq and ack
	seq = 0
	ack = len(msg)

	while msg:
		msg_f = f.read(576)
		# create packet with corresponding sequence_number, ack_number, SYN and FIN flags
		if (msg_f):
			packet = create_packet(seq, ack, 0, count, msg)
		else:
			packet = create_packet(seq, ack, 1, count, msg)
		seq += len(msg)
		ack += len(msg)
		packets.append(packet)
		msg = msg_f
		count += 1
	
	f.close()
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind(('0.0.0.0', ackport))

	# start sending packets
	client_main_thread(sock)
	print("All packets transmitted to server.")
	sock.close()