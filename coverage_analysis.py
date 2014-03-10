import os
import ast
import coverage
import numpy as np
import matplotlib.pyplot as plt
from coverage.parser import CodeParser
from operator import itemgetter


# Path of package
cwd = os.getcwd()
cut = len(cwd) + 1

# Get list of measured files
d = coverage.CoverageData()
d.read_file(cwd + '/.coverage')
measured_files = d.measured_files()
# Sort them alphabetically
measured_files.sort()

### Defintions
# Give subpack name from path
def subpack(path):
    start = path.index('/') + 1
    
    # For files which are not in subpackages
    if '/' not in path[start:]:
        end = len(path)
    else:
        end = path.index('/', start)
               
    return path[start:end]

# Give function names, start- and endlines for a file
# Can handle functions and functions in classes
def functions(file):
    func_name = []
    func_start = []
    func_end = []
    
    # Source, Lines and Code(List of Nodes)
    source = open(file, 'r').read()
    node_list = ast.parse(source).body
    line_list = source.splitlines()
    
    # Loop over code-nodes
    for i in range(len(node_list)):
        node = node_list[i]
        clas = type(node) == ast.ClassDef 
        func = type(node) == ast.FunctionDef

        last_node = i == (len(node_list) - 1)
        
        # If node is a class
        if clas:
            c_node_list = node.body
            # Starting line of class
            c_start = node.lineno
            # Name of class
            # (line_list is 0 based, .lineno is 1 based)
            c_name = line_list[c_start - 1]
            
            # There my be decorators before the real class
            # so find the 'real' starting line to get class-name
            while 'class ' not in c_name:
                c_start += 1
                c_name = line_list[c_start - 1]

            # Starting letter of class-name
            c_name_start = c_name.index('class') + 6
            
            # Either class Name(...):
            # or     class Name:
            if '(' not in c_name:
                c_name_end = c_name.index(':')
            else:
                c_name_end = c_name.index('(')
            
            # class-name
            c_name = c_name[c_name_start: c_name_end]
            
            # Loop over class-nodes
            for j in range(len(c_node_list)):
                c_node = c_node_list[j]
                c_func = type(c_node) == ast.FunctionDef
                last_c_node = j == (len(c_node_list) - 1)
            
                # If class-node is a function
                if c_func:
                    # Starting line of function
                    start = c_node.lineno
                    
                    # End line of function
                    # Maybe last class-node
                    if last_c_node:
                        # Maybe also last file-node
                        if last_node:
                            # Number of total lines in file
                            total_lines = len(line_list)
                            end = total_lines
                        # If only last node in class
                        else:
                            next_node = node_list[i+1]  
                            end = next_node.lineno - 1
                    # If there are more class-nodes    
                    else:
                        next_c_node = c_node_list[j+1]
                        end = next_c_node.lineno - 1
                
                    # Funcion name
                    name = line_list[start - 1]
                    # As above, watch out for decorators
                    while 'def ' not in name:
                        start += 1
                        name = line_list[start - 1]
                    
                    name_start = name.index('def') + 4
                    name_end = name.index('(')
                    f_name = name[name_start: name_end]
                    
                    # Merge class- and function-name like path
                    name = c_name + '/' + f_name
            
                    # Save name, start and end line of each function
                    func_name.append(name)
                    func_start.append(start)
                    func_end.append(end)
        
        # If node is function             
        elif func:
            # Starting line of function
            start = node.lineno
            
            # End line of function
            # May be last node in file
            if last_node:
                total_lines = len(line_list)
                end = total_lines    
            # or there is more to come
            else:
                next_node = node_list[i+1]  
                end = next_node.lineno - 1
            
            # Function-name
            name = line_list[start - 1]
            # Watch out for decorators
            while 'def ' not in name:
                start += 1
                name = line_list[start - 1]
            
            name_start = name.index('def') + 4
            name_end = name.index('(')
            name = name[name_start: name_end]
            
            # Save name, start and end line of function
            func_name.append(name)
            func_start.append(start)
            func_end.append(end)
    
    return func_name, func_start, func_end

# Get function coverage
# Input: Executable and executed lines in file and lines of functions
# Output: List of #statements and #missing-lines per function 
def function_coverage(executable, executed, func_start, func_end):
    miss_l = []
    stat_l = []
    
    # Loop over functions
    for i in range(len(func_start)):
        miss = 0
        stat = 0
        
        # Lines in function
        function_lines = range(func_start[i], func_end[i] + 1)
        
        # Loop over function-lines
        for line in function_lines:
            # Check if execuatble, missing (not executed)
            statement = line in executable
            missing = line not in executed
            
            # If execuatble -> Statement
            # and also missing -> not covered
            if statement:
                if missing:
                    miss += 1
                stat += 1

        miss_l.append(miss)
        stat_l.append(stat)
    
    return stat_l, miss_l
    

### Make files    
file_coverage = open('file_coverage.txt', 'w')
subpack_coverage = open('subpack_coverage.txt', 'w')
func_coverage = open('func_coverage.txt', 'w')
worst_func = open('worst_functions.txt', 'w')

# Lists for plotting
total_func_lines = []
covered_func_lines = []

# Init
sub_list = []
sub_exec = []
sub_miss = []
func = []
worst = 0.
number_of_functions = 0.
new_sub = False
last_file = measured_files[-1]

# Loop over measured files
for measured_file in measured_files:
    # Due to sorting the functions in one subpackage by coverage
    # this makes sure the last subpackage is also written
    last = measured_file == last_file
    path_cut = measured_file[cut:]
    
    # Number of executed lines per file
    executed_dic = d.executed_lines(measured_file)
    executed = float(len(executed_dic))
    
    # Number of executable line per file
    source = open(measured_file, 'r').read()
    
    # Fix if file is empty
    if source == '':
        executable = 0.
    else:
        # Get dictionary of executable lines
        c = CodeParser(source)
        executable_dic, excluded_dic = c.parse_source()
        executable = float(len(executable_dic))
        
    # Brackets over multiple lines are treated like more than one
    # executed line but only as one executable, so this has to be
    # corrected. There can only be as much executed lines as there
    # are executable.
    if executed > executable:
        fix = executed - executable
        executed += -fix
    
    # Zero division fix if there are no executable lines
    if executable == 0:
        coverage = '100%\n'
    else:
        coverage = str(int(executed / executable * 100)) + '%\n'
    
    # Number of missing lines in file
    missing = executable - executed
    
    # Subpack-Calculations
    # Find subpack-name
    sub = subpack(path_cut)
    
    # Make list of subpacks
    # If known, add number of executable and missing lines
    if sub in sub_list:
        ind = sub_list.index(sub)
        sub_exec[ind] += executable
        sub_miss[ind] += missing
        new_sub = False
    # If new, add to list
    else:
        # For Function-Calculations:
        # Don't write to file although first subpack is new
        if sub_list != []:
            new_sub = True
        sub_list.append(sub)
        sub_exec.append(executable)
        sub_miss.append(missing)
        
    # Function-Calculations
    # If new subpack
    if new_sub:
        # Sort multidim-list after coverage
        func.sort(key=itemgetter(3))
        number_of_functions += len(func)
        
        # Write every function to file
        for m in range(len(func)):
            # Coverage is at first an integer due to sorting
            f_cov_str = str(func[m][3]) + '%\n'
            func_write = '{0:<80s}{1:5d}{2:6d}{3:>8s}'.format(func[m][0], func[m][1], func[m][2], f_cov_str)
            func_coverage.write(func_write)
            
            # Worst functions list (>10 lines, <50% coverage)
            if func[m][1] > 10 and func[m][3] < 50:
                worst += 1
                worst_func.write(func_write)    
                
        # Make room for new subpack
        func = []
    
    # Using the predefined functions (every output is a list)    
    func_name, func_start, func_end = functions(measured_file)
    func_stats, func_miss = function_coverage(executable_dic, executed_dic, func_start, func_end)
    
    # Plot
    total_func_lines += func_stats
    for l in range(len(func_stats)):
        # Calculate number of covered lines
        covered = func_stats[l] - func_miss[l]
        covered_func_lines.append(covered)
        
    # Final function information
    for j in range(len(func_stats)):
        # Join path and function-name together
        func_path = path_cut + '/' + func_name[j]
        # Zero division fix
        if func_stats[j] == 0:
            func_cov = 100
        else:
            func_cov = int((1 - float(func_miss[j]) / float(func_stats[j])) * 100)
        
        # Add all to subpack-array for sorting and writing   
        func.append([func_path, func_stats[j], func_miss[j], func_cov])
          
    # The usual function-writing loop is only executed when a new subpack comes around,
    # theres has to be an extra one to also write the last subpack and it can't be in
    # the same position as the usual, because the last file hasn't been checked yet
    if last:
        func.sort(key=itemgetter(3))
        number_of_functions += len(func)
        
        for k in range(len(func)):
            func[k][3] = str(func[k][3]) + '%\n'
            func_write = '{0:<80s}{1:5d}{2:6d}{3:>8s}'.format(func[k][0], func[k][1], func[k][2], func[k][3])
            func_coverage.write(func_write)
            
            # Worst functions list (>10 lines, <50% coverage)
            if func[k][1] > 10 and func[k][3] < 50:
                worst += 1
                worst_func.write(func_write)

    # Writing to file
    file_write = '{0:<50s}{1:5d}{2:6d}{3:>8s}'.format(path_cut, int(executable), int(missing), coverage)
    file_coverage.write(file_write)

# Subpackages
# Loop to write subpackage file
for i in range(len(sub_list)):
    # Calculate subpackage coverage
    if sub_exec[i] == 0:
        sub_covr = '100%\n'
    else:
        sub_covr = str(int((1 - sub_miss[i]/sub_exec[i]) * 100)) + '%\n'
        
    # Writing to file    
    write = '{0:<20s}{1:5d}{2:6d}{3:>8s}'.format(sub_list[i], int(sub_exec[i]), int(sub_miss[i]), sub_covr)
    subpack_coverage.write(write)

file_coverage.close()
subpack_coverage.close()
func_coverage.close()
worst_func.close()

print "\n    Created 'file_coverage.txt'"
print "    Created 'func_coverage.txt'"
print "    Created 'worst_functions.txt'"
print "    Created 'subpack_coverage.txt'"


### Plot function coverage
# Limits
xmax = np.amax(np.array(total_func_lines)) * 1.1
xmin = -10.
ymax = np.amax(np.array(covered_func_lines)) * 1.1
ymin = -10.

# Orientation lines
x = np.linspace(0.,xmax)
y1 = 0.5 * x
y2 = 0.25 * x
y3 = 0.1 * x
y4 = 0.75 * x
plt.plot(x,x,label='100%')
plt.plot(x,y4,label='75%')
plt.plot(x,y1,label='50%')
plt.plot(x,y2,label='25%')
plt.plot(x,y3,label='10%')

# Plot
plt.scatter(total_func_lines, covered_func_lines)
plt.title('Function Coverage')
plt.xlabel('Statements')
plt.ylabel('Covered Lines')
plt.xlim(xmin,xmax)
plt.ylim(ymin,ymax)
plt.legend(loc=2)

# Saving plot
plt.savefig('function_coverage.pdf')
print "    Created 'function_coverage.pdf'\n"

per = str(int(worst/number_of_functions * 100))
worst = int(worst)
number = int(number_of_functions)

print '   ', len(measured_files), 'measured files'
print '   ', number, 'functions [' + str(worst) + '(' + per + '%) have bad coverage -> worst_functions.txt]'
print ''