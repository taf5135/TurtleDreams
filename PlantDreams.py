import argparse
import hashlib
import re
import turtle as t

#takes an arbitrary input, hashes it, and converts the 256-bit hash into an L-system
#then draws the L-system in stages as the user dictates
#press Up to draw instantly, Down to draw slowly. Press Enter to go to the next generation

#L-system takes in a mapping of cells to cells (dict), a seed, and a number of iterations
#at each iteration, go through the current cell list, starting with the seed, and replace each cell
#by its mapped counterpart. 
#then we can convert the produced set of cells into a plant by interpreting each as a command
#for the turtle. 

#The core of the L-system is the mapping. Therefore, we should make the mapping our randomly generated
#thing. We hash the input using SHA-256 and convert it to rules as follows.

#A hash consists of 32 bytes, or 64 half-bytes (nibbles)
#The first 3 bits control the number of chars, 2-7. The next 5 bits control the flower color. The remaining 62 nibbles are processed by the pushdown automata
#The pushdown automata splits the sequence of nibbles into sections, one for each rule, and processes each section into a rewriting string
#Based on the character just written and the height of the stack, we use the next nibble to transition into another state and write that state's character.
#We allow for early stopping. Excess characters that do not change the appearance are optimized out (ex. AB[+-&&-] -> AB)
#58 nibbles are used for rules. Leftover nibbles (4) define the seed. We remove all functional (non-letter) characters that are outside of square brackets

"""
Library of actions:
   F	         Move forward by line length drawing a line. ANY character does this
   +	         Turn left by turning angle
   -	         Turn right by turning angle
   [	         Push current drawing state onto stack
   ]	         Pop current drawing state from the stack
   @	         Draw a dot with line width radius
   &	         Swap the meaning of + and -
   (	         Decrement turning angle by turning angle increment
   )	         Increment turning angle by turning angle increment
"""

BASE_LENGTH = 10
BASE_ANGLE = 30
BASE_FLOWER_RAD = 2
FLOWERS_ONLY_AT_TIP = False

ANGLE_INCREMENT = 4

RULE_CHARS = "ABCDEFG"
START_CHAR = "." #Special character to signal we're in the start state
STOP_CHAR = '~' #Force-stops the pushdown parser
RULE_SIZE_MAX = 15

COLORS = [
    "#A846A0", "#7D4FFF", "#8A71CE", "#FF7FED", 
    "#FFB766", "#FFD800", "#FFE14F", "#FF7A28",
    "#5EF1FF", "#FFECEA", "#FF877C", "#7C87FF",
    "#FF5E5E", "#FCFF54", "#DACCFF", "#8EC8FF",
    "#FFFFFF", "#FF99A1", "#FF3DAE", "#D756FF",
    "#FF757E", "#758EFF", "#9F4CFF", "#87FFFD",
    "#3D91FF", "#2172FF", "#FF26CC", "#FF7FEB",
    "#EE9EFF", "#FFC587", "#F9D8FF", "#FFF2CE"
]

BG_COLOR = "#E6D4B2"
STEM_COLOR = "#4C8033"

given_speed = 6

class LSystem():
    def __init__(self, mapping : dict, seed : str, scale : float = 1, color : str = "#FFFFFF") -> None:
        self.mapping = mapping
        self.seed = seed
        self.state = seed
        self.scale = scale
        self.color = color

    def get_next_state(self):
        #update the state. Both return it and update self.state

        nstate = ""
        for char in self.state:
            if char in self.mapping.keys(): #safety, ignores invalid chars
                nstate += self.mapping[char]
            else:
                nstate += char

        self.state = nstate
        return nstate
    
    def draw_state(self):
        swap_const = 1
        turning_modifier = 0
        stack = []
        for char in self.state:
            if char == '+':
                t.left((BASE_ANGLE + turning_modifier) * swap_const)
            elif char == '-':
                t.right((BASE_ANGLE + turning_modifier) * swap_const)
            elif char == '[':
                #needs to save position and direction on the stack
                stack.append((t.heading(), t.pos(), swap_const, turning_modifier))
            elif char == ']':
                t.penup()
                head, pos, swap_const, turning_modifier = stack.pop()
                t.setheading(head)
                t.goto(pos)
                t.pendown()
            elif char == '@':
                t.color(self.color) 
                t.begin_fill()
                t.circle(BASE_FLOWER_RAD/self.scale)
                t.end_fill()
                t.color(STEM_COLOR)
            elif char == '&':
                swap_const = -swap_const
            elif char == '(':
                turning_modifier -= ANGLE_INCREMENT
            elif char == ')':
                turning_modifier += ANGLE_INCREMENT
            else:
                t.forward(BASE_LENGTH/self.scale)

    def reset_and_advance(self):
        t.goto(0,0)
        t.clear() 
        t.setheading(90)
        self.get_next_state()
        self.draw_state()


def pushdown_parser(digest, empty_stack_transitions, nonempty_transitions):
    #Runs a pushdown automata for plants with only F, +, -, [, ], and @ operations (F is 2 to 7 different characters)

    #first 3 bits decide how many mapped characters there will be. Minimum 2, max 7
    first = digest[0]
    num_of_chars = (first>>5)&0x7
    if num_of_chars < 2:
        num_of_chars += 2

    #next 5 bits decide the color of any flowers.
    flower_color = COLORS[int(first & 0x1F)]
    
    #collate next 29 bytes into 58 nibbles, and partition them into num_of_chars different sections
    #the last 2 bytes define the 4-character seed
    rule_nibbles = bytes_to_nibbles(digest[1:30])
    
    partition_size = 58 // num_of_chars

    available_chars = RULE_CHARS[:num_of_chars]

    #rectify the transition rules by changing unavailable chars into their equivalents
    empty_stack_transitions = rectify_transition(empty_stack_transitions, available_chars)
    nonempty_transitions = rectify_transition(nonempty_transitions, available_chars)

    stack = 0
    rules = {}
    for idx, char in enumerate(available_chars):
        state = '.'
        rule = ""
        for i in range(min(RULE_SIZE_MAX,partition_size)):
            current_nibble = rule_nibbles[idx * partition_size + i]
            if stack == 0:
                next_char = empty_stack_transitions[state][current_nibble]
            else:
                next_char = nonempty_transitions[state][current_nibble]

            if next_char == '[':
                stack += 1
            elif next_char == ']':
                stack -= 1

            if next_char == STOP_CHAR:
                break

            rule += next_char
            state = next_char
        
        rule += ']' * stack #pop the rest of the stack
        rules[char] = rule
        stack = 0

    #remaining nibbles define the seed
    seed_nibbles = bytes_to_nibbles(digest[30:])
    seed = "".join(available_chars[nib % num_of_chars] for nib in seed_nibbles)

    for key in rules.keys():
        rules[key] = cleanup_rule(rules[key])

    return rules, seed, flower_color

def cleanup_rule(rule):
    newrule = rule
    while newrule != re.sub(r"\[[\+\-\&\(\)]*\]", "", newrule): 
        newrule = re.sub(r"\[[\+\-\&\(\)]*\]", "", newrule)

    return re.sub(r"[\+\-\&\(\)]+\]","]",newrule) 

def bytes_to_nibbles(in_bytes):
    n = []
    for b in in_bytes:
        n.append(int(b>>4 & 0xF))
        n.append(int(b & 0xF))
    return n

def rectify_transition(tran, available_chars): #TODO maybe refactor this
    newtran = {}
    for key in tran.keys(): #maps rule chars to available chars based on their index % num_of_chars
        rule = tran[key]
        newrule = ""
        for char in rule:
            replacement = char
            if char in RULE_CHARS and char not in available_chars:
                replacement = available_chars[RULE_CHARS.index(char) % len(available_chars)] 
            newrule += replacement
        newtran[key] = newrule

    return newtran

def plant_to_file(fname : str, lsys : LSystem):
    try:
        with open(fname, 'w') as f:
            for key in lsys.mapping.keys():
                f.write(f"{key} : {lsys.mapping[key]}\n")
            f.write("\n")
            f.write(f"{lsys.seed}\n")
            f.write(f"{lsys.color}")
    except Exception as e:
        print(f"Could not dump to file: {e}")

def plant_from_file(fname : str):
    try:
        with open(fname, 'r') as f:
            rules = {}
            while (line := f.readline().strip()) != "":
                l = line.split(":")
                key = l[0].strip()
                val = l[1].strip().replace(".","")
                rules[key] = val
            seed = f.readline().strip()
            color = f.readline().strip()
        return rules, seed, color
    except Exception as e:
        print(f"Could not read from file: {e}")
        print("Check to make sure the file exists and is not malformed")
        return None, None, None

def speed_up():
    t.speed("fastest")
    t.tracer(0,0)

def speed_down():
    t.tracer(1, 25)
    t.speed(given_speed)

def zoom_in():
    width, height = win.screensize()
    win.screensize(width / 1.5, height / 1.5)

def zoom_out():
    width, height = win.screensize()
    win.screensize(width * 1.5, height * 1.5)

def produce_system_from_string(user_input, use_full_parser=False):
    hasher = hashlib.sha256()
    hasher.update(user_input.encode('utf-8'))

    digest = hasher.digest()

    #represents a transition matrix
    #since the stack is only relevant to one character, we can use this to simplify the code
    empty_stack_transitions_6op = {
         "."    :   "ABCDEFGAB[[[[DFG"
        ,"A"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "+["
        ,"B"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "[-"
        ,"C"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "+["
        ,"D"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "[-"
        ,"E"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "+["
        ,"F"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "[-"
        ,"G"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "+["
        ,"+"    :   "ABCDEFG+A[+D@" + STOP_CHAR + "+["
        ,"-"    :   "ABCDEFGB-[C-@" + STOP_CHAR + "[-"
        ,"]"    :   "ABCD[[[@@[EF@" + STOP_CHAR + "G["
        ,"@"    :   "ABCDEFG[[[EFG" + STOP_CHAR + "+-"
    }

    nonempty_transitions_6op = {
         "A"    :   "ABCDEFG+-[]A@" + STOP_CHAR + "]-"
        ,"B"    :   "ABCDE-G+-[]B@" + STOP_CHAR + "+]"
        ,"C"    :   "ABCD+FG+-[]C@" + STOP_CHAR + "[-"
        ,"D"    :   "ABC-EFG+-[]D@" + STOP_CHAR + "+]"
        ,"E"    :   "AB+DEFG+-[]E@" + STOP_CHAR + "[-"
        ,"F"    :   "A-CDEFG+-[]F@" + STOP_CHAR + "+]"
        ,"G"    :   "+BCDEFG+-[]G@" + STOP_CHAR + "]-"
        ,"+"    :   "ABCDEFG+A[BD@E+F"
        ,"-"    :   "ABCDEFGB-[CD@FG-"
        ,"["    :   "+-+-+-C+-[+-+-+-"
        ,"]"    :   "ABCD[[[]-[+-@" + STOP_CHAR + "[]"
        ,"@"    :   "AB]]]]G+-[+--" + STOP_CHAR + "+-"
    }

    empty_stack_transitions_full = {
         "."    :   "ABCDEFGAB[[[[DFG"
        ,"A"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "&)" 
        ,"B"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "(&"
        ,"C"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "&)"
        ,"D"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "(&"
        ,"E"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "&)"
        ,"F"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "(&"
        ,"G"    :   "ABCDEFG[[[[[@" + STOP_CHAR + "&)"
        ,"+"    :   "ABCDEFG+A[+[@" + STOP_CHAR + "(&"
        ,"-"    :   "ABCDEFGB-[C[@" + STOP_CHAR + "&)"
        ,"]"    :   "ABCD[[[@@[E[@" + STOP_CHAR + "(&"
        ,"@"    :   "ABCDEFG[[[E[G" + STOP_CHAR + "&)"
        ,"&"    :   "ABCDEFG+-[[-@" + STOP_CHAR + "()" 
        ,"("    :   "ABCDEFG+-[[&@" + STOP_CHAR + "(@"
        ,")"    :   "ABCDEFG+-[[&@" + STOP_CHAR + "@)" 
    }

    nonempty_transitions_full = {
         "A"    :   "ABCDEFG+-[]&@" + STOP_CHAR + "()"
        ,"B"    :   "ABCDE-G+-[]&@" + STOP_CHAR + "()"
        ,"C"    :   "ABCD+FG+-[]&@" + STOP_CHAR + "()"
        ,"D"    :   "ABC-EFG+-[]&@" + STOP_CHAR + "()"
        ,"E"    :   "AB+DEFG+-[]&@" + STOP_CHAR + "()"
        ,"F"    :   "A-CDEFG+-[]&@" + STOP_CHAR + "()"
        ,"G"    :   "+BCDEFG+-[]&@" + STOP_CHAR + "()"
        ,"+"    :   "ABCDEFG+A[B&@E+F"
        ,"-"    :   "ABCDEFGB-[C&@FG-"
        ,"["    :   "+-+-+-C+-[+-+-+-"
        ,"]"    :   "ABCD[[[]-[+&@" + STOP_CHAR + "[]"
        ,"@"    :   "AB]]]]G+-[+&-" + STOP_CHAR + "+-"
        ,"&"    :   "ABCDEFG+-[[+@" + STOP_CHAR + "()" 
        ,"("    :   "ABCDEFG+-[[&@" + STOP_CHAR + "(E"
        ,")"    :   "ABCDEFG+-[[&@" + STOP_CHAR + "F)"
    }

    if use_full_parser:
        rules, seed, flower_color = pushdown_parser(digest, empty_stack_transitions_full, nonempty_transitions_full)
    else:
        rules, seed, flower_color = pushdown_parser(digest, empty_stack_transitions_6op, nonempty_transitions_6op)

    if FLOWERS_ONLY_AT_TIP:
        rules['@'] = ''

    print("Rules: \n" + str(rules))
    print("Seed: " + seed)
    print("Color: " + flower_color)
    
    return LSystem(rules, seed, 1, flower_color)

def main(args, win : t._Screen, gstr : str = None):

    scale = args.scale
    depth = args.depth

    if args.read:
        rules, seed, color = plant_from_file(args.read)
        lsys = LSystem(rules, seed, color=color)
    elif args.genstring:
        lsys = produce_system_from_string(args.genstring, args.full)
    else:
        lsys = produce_system_from_string(gstr, args.full)

    if args.dumpto:
        plant_to_file(args.dumpto, lsys)

    lsys.scale = scale

    t.left(90) #grow upwards
    win.screensize(3000, 2000)

    if depth is not None:
        for _ in range(depth):
            lsys.get_next_state()
        speed_up()
        lsys.draw_state()
        speed_down()

    win.onkey(lsys.reset_and_advance, "Return")
    win.onkey(speed_up, "Up")
    win.onkey(speed_down, "Down")
    win.onkey(zoom_in, "-")
    win.onkey(zoom_out, "+")

    win.listen()
    win.mainloop()



if __name__ == '__main__':

    parser = argparse.ArgumentParser("Talk to the turtle and grow a procedurally-generated plant based on your input. \nUP to speed up, DOWN to speed down, ENTER to go to next generation")
    parser.add_argument("--speed", "-s", help="Drawing speeed of the turtle. -1 for instant image generation", type=int, default=6)
    parser.add_argument("--scale", "-c", help="Custom scale factor for the drawing. Line length = default size/scale factor. Default 1", type=float, default=1)
    parser.add_argument("--depth", "-d", help="Jump to a depth immediately instead of showing each growth stage", type=int)
    parser.add_argument("--read", "-r", help="Specify a plant file to read and draw instead of accepting input from stdin", type=str)
    parser.add_argument("--dumpto", "-t", help="Write the generated ruleset, seed, and color to a file", type=str)
    parser.add_argument("--tipflowers", "-f", help="Flowers last only for the generation that produced them. Default false", action="store_true")
    parser.add_argument("--full", "-l", help="Use full (9-operation) parser", action="store_true")
    parser.add_argument("--genstring", "-g", help="Generation string to use instead of asking stdin. Use quotation marks for a longer input")

    args = parser.parse_args()

    FLOWERS_ONLY_AT_TIP = args.tipflowers

    genstring = args.genstring
    if not args.genstring and not args.read:
        genstring = input("Input generation string: ")

    try:
        win = t.Screen()
        win.title("PlantDreams")
        win.bgcolor(BG_COLOR)
        win.screensize(3000, 2000)
        t.color(STEM_COLOR)

        if args.speed == -1:
            t.tracer(0, 0)
            t.speed("fastest")
        else:
            given_speed = min(10, max(0, args.speed))
            t.speed(given_speed)
    
        main(args, win, genstring) 

    except t.Terminator:
        pass #Don't show error if user closes window prematurely
