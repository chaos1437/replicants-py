def interpreter(code, x=0, y=0):
    registers = [0, 0, 0, 0]
    current_register = 0

    for command in code:
        match command:
            case "+":
                registers[current_register] += 1
            
            case ">":
                current_register += 1
                if current_register > 3:
                    current_register = 0
        
            case "<":
                current_register -= 1
                if current_register < 0:
                    current_register = 3
        
        print(x, y, registers)
    
    direction = registers.index(max(registers))

    match direction:
        case 0:
            x -= 1
        case 1:
            y += 1
        case 2:
            x += 1
        case 3:
            y -= 1
    
    return x, y

x, y = interpreter("+>+>+>+>+")
print(x, y)




