#-*- coding: utf-8 -*-

import sys
import os
import re
import xlrd
from common import get_str_from_sheet

import sys
reload(sys)
sys.setdefaultencoding( "utf-8" )

#TODO: 

# 类型表
dicType = {}

#记录每个子类型的具体的数据类型
subType2Type= {}

# 流水表
allFlow = {}

line_start = "//=================auto generate start dblog==================="
line_end = "//=================auto generate end dblog====================="

subtype_line_start = "//=================auto generate start sub type==================="
subtype_line_end = "//=================auto generate end dblog sub type====================="

def usage():
	print """
	python tools/autocode/dblog/gen_dblog_format.py ./ tmp/导表数据/dblog.xlsx Log描述 module/dblog/format.c 
	"""

type2format = { 
	u'string':"%s",
	u'int':"%d",
	u'datetime':"%s",
	u'float':"%f",
}

type_template = u"""

mapping typeInfo = {
"""

simple_func_template = u"""
void DbLog%s(object oUser)
{
	"module/dblog/main"->DbLogInfo(%s, %s, oUser);  
}
"""


func_template = u"""
void DbLog%s(object oUser, %s)
{
	//检查参数类型
%s
	"module/dblog/main"->DbLogInfo(%s, %s, oUser, %s);  
}
"""

def parse_type_sheet(sh, sheetName, dicType):
	dicType[sheetName] = {}
	subType2Type[sheetName] = {}
	typeDict = {}
	for row in range(1, sh.nrows):
		key = ""
		for col in range(0, sh.ncols):
			head = get_str_from_sheet(sh, 0, col)
			value = get_str_from_sheet(sh, row, col)
			if head == "Name":
				key = get_str_from_sheet(sh, row, 0)
				if len(key) == 0: continue
				typeDict[key] = {};
			else:
				#print head
				typeDict[key][head] = value
				#记录自定义类型的数据类型
				#if head == "Type" and not typeDict.has_key(head):
				#	typeDict[head] = value
				if head == "Type" and not subType2Type[sheetName].has_key(head):
					subType2Type[sheetName][head] = value

	dicType[sheetName] = typeDict 

def parse_dblog_dsc(sh, dicType):
	allTypeKeys = dicType.keys()
	for row in range(1, sh.nrows):
		key = ""
		for col in range(0, sh.ncols):
			head = get_str_from_sheet(sh, 0, col)
			value = get_str_from_sheet(sh, row, col)
			if len(value) == 0: continue
			if head == u"日志动作":
				key = get_str_from_sheet(sh, row, 0)
				allFlow[key] = {}
			else:
				allFlow[key][head] = value	

def write_type_file(subType, finalStr):
	tmp = []
	flag = 1
	curDir = os.getcwd()
	#print subType
	#print curDir
	dblogDir = "module/dblog/subType/"
	fileName = "module/dblog/subType/%s.c"%(subType)
	createFileCmd = "touch %s" % (fileName)
	#print createFileCmd
	if not os.path.isdir(dblogDir):
		os.system("mkdir -p " + dblogDir)

	os.system(createFileCmd)

	#print fileName
	fd = file(fileName, "r")
	filelines = fd.readlines()
	#print len(filelines)
	if len(filelines) == 0:
		tmp.append(subtype_line_start)
		tmp.append("\n")
		tmp.append(subtype_line_end)
		tmp.append("\n")
		fd.close()
		fd = file(fileName, "w")
		fd.write("".join(tmp))
		fd.close()

	tmp = []
	fd = file(fileName, "r")
	filelines = fd.readlines()
	for line in filelines:
		if flag == 1:
			tmp.append(line)
		if flag and subtype_line_start in line:
			tmp.append(finalStr)
			tmp.append("\n")
			flag = 0
		if not flag and subtype_line_end in line:
			tmp.append(line)
			flag = 1
	fd.close()
	fd = file(fileName, "w")
	fd.write("".join(tmp))
	fd.close()




def gen_subtype_format():
	#导类型表
	for subType in dicType.keys():
		result = []
		subTypeInfo = dicType[subType]	
		#print subTypeInfo
		result.append(type_template)



		type_info = list(subTypeInfo.iteritems())
		type_info.sort(key = lambda x:int(x[1]["Value"]))

		for key in type_info:
			if key[0] == "Type": continue
			name = key[0]
			desc = key[1][u"NameCN"]
			#print desc
			value = key[1]["Value"]
			type = key[1]["Type"]
			
			mapKeyDesc = "\t//%s"%(desc)
			#print mapKeyDesc
			#typeInfo.append(mapKeyDesc)
			mapKeyData = '''\t"%s" : %s,'''%(name, value)
			#typeInfo.append(mapKeyData)
			result.append(mapKeyDesc)
			result.append(mapKeyData)
		result.append("}")
		result.append("#include <dblog_subType_func.h>\n")
		finalStr = "\n".join(result)
		write_type_file(subType, finalStr)



# 导整个表
def parse_xls(filename, sn, output_path):
	try:
		book = xlrd.open_workbook(filename)
	except:
		msg = u"can't open file? %s"%filename
		#print( msg )
		usage()
		raise

	# 遍历xls
	for x in xrange(book.nsheets):
		sh = book.sheet_by_index(x)
		sheetName = sh.name
		#print( sheetName )
		# 优先导类型表表
		if sheetName != u"Log描述":
			parse_type_sheet(sh, sheetName, dicType)
	
	gen_subtype_format()

	#导流水表
	for x in xrange(book.nsheets):
		sh = book.sheet_by_index(x)
		sheetName = sh.name
		if sheetName != u"Log描述":
			continue
		parse_dblog_dsc(sh, dicType)


def gen_func_args_str(filedKey, filedDsc, filedType, filedSize, idx, maxSize):
	if idx == maxSize-3:
		return "%s"%(filedKey)
	else:
		return "%s,"%(filedKey)


def gen_func_args(flow):
	result = []
	maxSize = len(allFlow[flow])
	idx = 0

	flow_infos = list(allFlow[flow].iteritems())
	flow_infos.sort()
	for flow_info in flow_infos:
		key = flow_info[0]
		info = flow_info[1]
		if key != u"名字" and key != "uid" and key != u"验证渠道":
			filedMsg = info.split(";")
			if len(filedMsg) != 4:
				#print filedMsg
				sys.exit(1)

			filedKey = filedMsg[0]
			filedDsc = filedMsg[1]
			filedType = filedMsg[2]
			if subType2Type.has_key(filedType):
				filedType = subType2Type[filedType]["Type"]
			filedSize = filedMsg[3]
			idx += 1
			oneArgStr = gen_func_args_str(filedKey, filedDsc, filedType, filedSize, idx, maxSize)

			result.append(oneArgStr)
	return " ".join(result)


def gen_check_func_str(flow, filedKey, filedDsc, filedType, filedSize):
	return "\tCheck%s(%s, \"DbLog%s %s ERROR\");\n" % (filedType, filedKey, flow, filedKey)


def gen_check_func(flow):
	result = []

	flow_infos = list(allFlow[flow].iteritems())
	flow_infos.sort()
	for flow_info in flow_infos:
		key = flow_info[0]
		info = flow_info[1]
		if key != u"名字" and key != "uid" and key != u"验证渠道":
			filedMsg = info.split(";")
			if len(filedMsg) != 4:
				print filedMsg
				sys.exit(1)

			filedKey = filedMsg[0]
			filedDsc = filedMsg[1]
			filedType = filedMsg[2]
			filedSize = filedMsg[3]
			oneArgStr = gen_check_func_str(flow, filedKey, filedDsc, filedType, filedSize)
			result.append("\n")
			result.append(oneArgStr)
	return "".join(result)


def gen_args_str(filedKey, filedDsc, filedType, filedSize, idx, maxSize):
	if idx == maxSize-3:
		return "%s %s"%(filedType, filedKey)
	else:
		return "%s %s,"%(filedType, filedKey)


def gen_args(flow):
	result = []
	maxSize = len(allFlow[flow])
	idx = 0

	flow_infos = list(allFlow[flow].iteritems())
	flow_infos.sort()
	for flow_info in flow_infos:
		key = flow_info[0]
		info = flow_info[1]
		if key != u"名字" and key != "uid" and key != u"验证渠道":
			filedMsg = info.split(";")
			if len(filedMsg) != 4:
				print filedMsg
				sys.exit(1)

			filedKey = filedMsg[0]
			filedDsc = filedMsg[1]
			filedType = filedMsg[2]
			if subType2Type.has_key(filedType):
				filedType = subType2Type[filedType]["Type"]
			filedSize = filedMsg[3]
			idx += 1
			oneArgStr = gen_args_str(filedKey, filedDsc, filedType, filedSize, idx, maxSize)
			result.append(oneArgStr)
	return " ".join(result)


#求优化
def gen_file_content():
	result = []
	for flow in allFlow.keys():
		print flow
		flowInfo = []
		#flowInfo.append(flow.upper()) 
		descArr = []

		#先插入uid的格式
		for key in allFlow[flow].keys():
			if key == "uid":
				filedMsg = allFlow[flow][key].split(";")
				if len(filedMsg) != 4:
					print filedMsg
					sys.exit(1)

				filedKey = filedMsg[0]
				filedDsc = filedMsg[1]
				filedType = filedMsg[2]
				if subType2Type.has_key(filedType):
					filedType = subType2Type[filedType]["Type"]
				filedSize = filedMsg[3]
				flowInfo.append(type2format[filedType])
				descArr.append(filedDsc)

		#在插入验证渠道的格式
		for key in allFlow[flow].keys():
			if key == u"验证渠道":
				filedMsg = allFlow[flow][key].split(";")
				if len(filedMsg) != 4:
					print filedMsg
					sys.exit(1)

				filedKey = filedMsg[0]
				filedDsc = filedMsg[1]
				filedType = filedMsg[2]
				if subType2Type.has_key(filedType):
					filedType = subType2Type[filedType]["Type"]
				filedSize = filedMsg[3]
				flowInfo.append(type2format[filedType])
				descArr.append(filedDsc)


		#先对字典做个排序
		flow_infos = list(allFlow[flow].iteritems())
		flow_infos.sort()
		for flow_info in flow_infos:
			key = flow_info[0]
			info = flow_info[1]
			if key != u"名字" and key != "uid" and key != u"验证渠道":
				filedMsg = info.split(";")
				if len(filedMsg) != 4:
					print filedMsg
					sys.exit(1)

				filedKey = filedMsg[0]
				filedDsc = filedMsg[1]
				filedType = filedMsg[2]
				if subType2Type.has_key(filedType):
					filedType = subType2Type[filedType]["Type"]
				filedSize = filedMsg[3]
				flowInfo.append(type2format[filedType])
				descArr.append(filedDsc)

		desc  = "//%s" % ("|".join(descArr))
		result.append(desc)
		macro = "#define %s %s \n"%(flow.upper(), "\"" + flow.lower() + "\"")
		result.append(macro)
		macro_fmt = "#define %s %s \n"%(flow.upper() + "_FMT", flow.upper() + "\"" + "|" + "|".join(flowInfo) + "\"")
		result.append(macro_fmt)
		
		
		maxSize = len(allFlow[flow])
		if maxSize == 3:
			result.append(simple_func_template % (flow, flow.upper(), flow.upper()+"_FMT"))
		else:
			result.append(func_template % (flow, gen_args(flow), gen_check_func(flow), flow.upper(), flow.upper()+"_FMT", gen_func_args(flow)))
			

	return "\n".join(result)


def write_file(output_path):
	#result.append(line_start)
	#result.append(line_end)
	create_file = "touch %s"%(output_path)
	os.system(create_file)

	tmp = []
	fd = file(output_path, "r")
	filelines = fd.readlines()
	#print len(filelines)
	if len(filelines) == 0:
		tmp.append(line_start)
		tmp.append("\n")
		tmp.append(line_end)
		fd.close()
		fd = file(output_path, "w")
		fd.write("".join(tmp))
		fd.close()

	tmp = []
	flag = 1
	fd = file(output_path, "r")
	for line in fd.readlines():
		if flag == 1:
			tmp.append(line)
		if flag and line_start in line:
			tmp.append(gen_file_content())
			tmp.append("\n")
			flag = 0
		if not flag and line_end in line:
			tmp.append(line)
			flag = 1
	fd.close()
	fd = file(output_path, "w")
	fd.write("".join(tmp))
	fd.close()

def gen_subtype_macro(macro_file):
	create_file = "touch %s"%(macro_file)
	os.system(create_file)
	
	with open(macro_file, "w") as fd:
		for sheet_name in dicType.keys():
			macro_all_desc = "//" + sheet_name
			fd.write("//=============================="+ "\n")
			fd.write(macro_all_desc)
			fd.write("\n")
			sheet_info = dicType[sheet_name]
			all_macros = list(sheet_info.iteritems())
			all_macros.sort(key = lambda x:int(x[1]["Value"]))
			for key_info in all_macros:
				key_name = key_info[0]
				name_info = key_info[1]
				macro_value = name_info["Value"]
				macro_desc = name_info["NameCN"]
				macro_key = (sheet_name + "_" + key_name).upper()
				macro_str = "#define %s (%s)"%(macro_key, macro_value)
				fd.write("//" + macro_desc + "\n")
				fd.write(macro_str)
				fd.write("\n")

if __name__ == "__main__":
	argv_len = len(sys.argv)
	if argv_len < 5:
		usage()
		sys.exit(1)
	
	root_path = sys.argv[1]
	filename = sys.argv[2]
	sheetname = sys.argv[3]
	output_path = sys.argv[4]
	parse_xls( filename, sheetname, output_path )
	write_file(output_path)

	macro_file = "include/dbtype_macro.h"
	#生成宏文件
	gen_subtype_macro(macro_file)
