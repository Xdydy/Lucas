# from dotenv import find_dotenv, load_dotenv
# load_dotenv(find_dotenv())
import os
import time
os.environ["FAASIT_PROVIDER"]="local-once"
from index import handler
inputData = {"text":"Hello world this is a happy day","batchSize":3}
start_time = time.time()
output = handler(inputData)
end_time = time.time()
print(output)
print(f"Execution time: {end_time - start_time} seconds")