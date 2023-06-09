from dnslib.server import DNSServer, DNSHandler, BaseResolver,  DNSLogger
from dnslib.dns import A,RR, DNSRecord
import os
import time
from socket import gethostbyname
from flask import Flask, request, redirect
import dns.resolver
import socket
import threading
import dnslib
import logging

OUTPUT_LOGFILE = "dnsfilter.log"

allowed_subdomains = []

HOST_KBPS = {}
LAST_BATCH_WINDOW = 0


def reload_allowed_subdomains():
	global allowed_subdomains
	with open("allowed_subdomains.txt") as f:
		allowed_subdomains = []
		for line in f:
			allowed_subdomains.append(line.split(" ")[0].strip())
			logging.info('added subdomain to allow list ' + line.split(" ")[0].strip())



    
class CustomResolver(BaseResolver):
	def resolve(self, request, handler):
		reply = request.reply()
		qname = request.q.qname
		qtype = request.q.qtype
		requester_ip = handler.server.socket.getsockname()[0]

		# Check if the query is for an A record for example.com
		if  self.is_subdomain_allowed(str(qname)[:-1],allowed_subdomains): #qname == "example.com":
			# Replace this with your own list of IP addresses

			ip_addresses = self.get_addr_list(str(qname))
			
#			up,down = HOST_KBPS[requester_ip]
#			HOST_KBPS[requester_ip] = up + len(qname), down + (len(ip_addresses) * 4)
#			if LAST_BATCH_WINDOW < (time.time() - 60):
#				HOST_KBPS[requester_ip]  = 0,0
#				LAST_BATCH_WINDOW = time.time()
		
			# Add a resource record for each IP address
			if len(ip_addresses):
				for ip_address in ip_addresses:
					reply.add_answer(RR(qname, ttl=60, rdata=A(ip_address)))
			else:
				logging.info('unable to resolve allowed subdomain ' + str(qname))
				reply.header.set_rcode(dnslib.RCODE.NXDOMAIN)
		else:
			logging.info('denied request for qname ' + str(qname))
			reply.header.set_rcode(dnslib.RCODE.NXDOMAIN)

		# Return the DNS response
		return reply

	def is_subdomain_allowed(self, subdomain, reference_list):
		subdomain_parts = subdomain.split('.')
		for i in range(len(subdomain_parts)):
			current_subdomain = '.'.join(subdomain_parts[i:])
			if current_subdomain in reference_list:
				return True
		return False

		

	def get_addr_list(self,domain_name):
		ip_addresses = []
		if domain_name is not None:
			try:
				addr_info = socket.getaddrinfo(domain_name, None, socket.AF_INET, socket.SOCK_STREAM)
				for info in addr_info:
					ip_addresses.append(info[4][0])
			except socket.gaierror: #couldnt resolve an allowed host
				pass
		return ip_addresses



# Define Flask app
app = Flask(__name__)

@app.route("/")
def home():
	# Read in the current list of allowed subdomains
	allowed_subdomains_str = "<table>" #<input type=submit value=delete><br>".join(allowed_subdomains)

	for l in allowed_subdomains:
		allowed_subdomains_str += "<tr><td>" + l + "</td><td><button type=\"submit\" formaction=\"/delete?subdomain="+l+"\">Delete</button></td></tr>"
	allowed_subdomains_str += "</table>"
	# Render the template with the list of allowed subdomains
	return f"""
		<html>
			<head>
				<title>Allowed Subdomains</title>
			</head>
			<body>
				<h1>Allowed Subdomains</h1>
				<form>
				{allowed_subdomains_str}
				</form>
				<form method="post">
					<label>Add subdomain:</label>
					<input type="text" name="subdomain">
					<button type="submit">Add</button>
				</form>
			</body>
		</html>
	"""


@app.route("/delete", methods=["GET"])
def del_subdomain():
#	subdomain = request.form["subdomain"].strip()
#	print(subdomain)
#	if subdomain in allowed_subdomains:
#		del(allowed_subdomains[allowed_subdomains.index(subdomain)])
#		with open("allowed_subdomains.txt", "a") as f:
#			f.write(f"{new_subdomain}\n")
            
	return redirect("/")
	
	
def resolve_hostname(hostname):
    try:
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except socket.gaierror:
        return "127.0.0.1"
        
@app.route("/", methods=["POST"])
def add_subdomain():
	# Add the new subdomain to the list
	subdomain = request.args.get("subdomain")
	if new_subdomain not in allowed_subdomains:
		allowed_subdomains.append(new_subdomain)
	#        # Write the updated list of allowed subdomains to file
		with open("allowed_subdomains.txt", "a") as f:
			f.write(f"{new_subdomain} - %s\n" % resolve_hostname(new_subdomain))
		logging.info('added subdomain to allow list ' + new_subdomain)
	# Redirect back to the home page
	
	reload_allowed_subdomains()
	return redirect("/")

def dummylog(arg):
	pass



logging.basicConfig(filename=OUTPUT_LOGFILE, filemode='a',format='%(asctime)s - %(message)s', level=logging.INFO)
slogger = logging.StreamHandler()
slogger.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logging.getLogger().addHandler(slogger)

logging.info('startup')

reload_allowed_subdomains()

resolver = CustomResolver()
handler = DNSHandler
dlogger = DNSLogger(prefix=False,logf=lambda s:dummylog(s.upper()))
server = DNSServer(resolver, port=53, address='', logger=dlogger)


dns_thread = threading.Thread(target=server.start)
dns_thread.start()


app.run()
