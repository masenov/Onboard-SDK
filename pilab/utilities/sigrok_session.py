import zipfile
import io

class SigrokSession(object):
    def __init__(self):
        self.sigrok_version = "0.3.0"
        self.version = "2"
        self.sample_rate = 0
        self.data = None # Binary data
        
        self.data_file_name = "logic-1-1"
        
        self.metadata_template = (
              "[global]\n"
            + "sigrok version=%(version)s\n\n"
            + "[device 1]\n"
            + "capturefile=logic-1\n"
            + "total probes=8\n"
            + "samplerate=%(sample_rate)s Hz\n"
            + "probe1=0\n"
            + "probe2=1\n"
            + "probe3=2\n"
            + "probe4=3\n"
            + "probe5=4\n"
            + "probe6=5\n"
            + "probe7=6\n"
            + "probe8=7\n"
            + "unitsize=1"
        )
        
    def set_sigrok_version(self, version):
        self.sigrok_version = version
    
    def set_rate(self, rate):
        self.sample_rate = rate
        
    def set_data(self, data):
        self.data = data
        
    def generate_metadata(self):
        vals = { "version":self.sigrok_version, "sample_rate":self.sample_rate }
        new_metadata = self.metadata_template % vals
        return new_metadata
        
    def get_session_file(self):
        fileObject = io.BytesIO()
        zf = zipfile.ZipFile(fileObject, "w", zipfile.ZIP_DEFLATED, False)
        zf.writestr("metadata", self.generate_metadata())
        zf.writestr(self.data_file_name, str(self.data))
        zf.writestr("version", self.version)
        return fileObject     
