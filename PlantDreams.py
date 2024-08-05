import argparse
import hashlib
import turtle as t

#takes an arbitrary input, hashes it, and converts the 256-bit hash into an L-system
#then draws the L-system after a specified number of epochs
#L-system takes in a mapping of cells to cells (dict), a seed, and a number of iterations
#at each iteration, go through the current cell list, starting with the seed, and replace each cell
#by its mapped counterpart. 
#then we can convert the produced set of cells into a plant by interpreting each as a command
#for the turtle. 

#The core of the L-system is the mapping. Therefore, we should make the mapping our randomly generated
#thing.

#But first, let's try and implement one thats purely hardcoded. What operations should we support?
#turn left, turn right, forward, dot, and some kind of curve if possible
#"stack" behavior can be implemented as well (saving the current turtle state and returning to it later)
#basically the stuff from https://paulbourke.net/fractals/lsys/ but with no polygons (yet?)

#How will we do the randomization?
#One option: pre-build rules that work together, then use the hash to define what gets rewritten to what
#Option two: Have the hash build the rewriting rules, and then also have it define the mapping. This could be done as a next step to the first option
#In order build a single rule, we could use a stack machine to decide what symbol will be written next. This allows us some fine tuning to make "good" patterns
# more likely, such as making sure "+-" doesn't appear. It could also prevent "[[" from appearing. We will need extra logic to make sure that any "[" has a corresponding "]",
# and vice versa
# https://cs.rit.edu/~tjb/fsm.html has a good DFA maker that we can use to complete the steps

#How many rules should be possible? 2-7 seems like a good range. That means there are, if we implement everything, 17 possible next characters inside a given mapping
#We need to reduce this down to 16. By specifically crafting the pushdown machine to disallow certain transitions, we can force this number down
#But we need to reduce it for every possible character, which is difficult.

#The 32 bytes: first 3 bits control the number of chars. The next 5 bits control the flower color. The remaining 62 nibbles are processed by the pushdown automata
#We allow for early stopping. 
#Leftover nibbles define the seed. We remove all functional (non-letter) characters that are outside of square brackets

#POSSIBLE DESIGN OVERHAUL: (test '&' inclusion before you do it)
#We can try to compromise between "each nibble directly determines the next character" and "each byte just selects a good prebuilt rule"
#by having each nibble map to a sequence instead of a single character
#ex: 0000 maps to AB, 0001 to A[+B], 0010 to A[-B], 0011 to BB-A

#For a full feature set of 13 possible actions, we will need to allocate ~4 bits to each character. 
#
"""
Library of actions:
   F	         Move forward by line length drawing a line. ANY character does this
   +	         Turn left by turning angle
   -	         Turn right by turning angle
   [	         Push current drawing state onto stack
   ]	         Pop current drawing state from the stack

Ones below here are secondary features, to be implemented at your convenience:
   @	         Draw a dot with line width radius
   &	         Swap the meaning of + and -
   (	         Decrement turning angle by turning angle increment
   )	         Increment turning angle by turning angle increment
"""

BASE_LENGTH = 10
BASE_ANGLE = 30
BASE_FLOWER_RAD = 2

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

given_speed = 6

class LSystem():
    def __init__(self, mapping : dict, seed : str, scale : float, color : str = "#FFFFFF") -> None:
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
                head, pos, swap_const, turning_modifier = stack.pop() #If we add angle inc/dec, width inc/dec, flower color, or &, then we need to update the stack construction
                t.setheading(head)
                t.goto(pos)
                t.pendown()
            elif char == '@':
                t.color(self.color) 
                t.begin_fill()
                t.circle(BASE_FLOWER_RAD)
                t.end_fill()
                t.color(0.3, 0.5, 0.2) #TODO change these colors, dont bother using floats
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


#TODO so far this produces a lot of filamentous, snaggly plants. How can we promote branching? 
#TODO so far the plants tend to curl a lot in one direction, and spiral after only a few generations. How can we make them grow straight-ish? Will & work?
#Do we need to make + and - only possible inside square brackets?
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

    #represents a transition matrix
    #since the stack is only relevant to one character, we can use this to simplify the code
    #TODO may need to change this later if we want more complex behavior (e.g only writing ] if we have already written a rule char)
    
    

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
    #TODO this is kind of duplicated code
    seed_nibbles = bytes_to_nibbles(digest[30:])
    seed = "".join(available_chars[nib % num_of_chars] for nib in seed_nibbles) #TODO: this means all plants start as a long stick. Need something more complex

    return rules, seed, flower_color

def bytes_to_nibbles(in_bytes):
    n = []
    for b in in_bytes:
        n.append(int(b>>4 & 0xF))
        n.append(int(b & 0xF))
    return n

def rectify_transition(tran, available_chars): #TODO maybe refactor this
    newtran = {}
    for key in tran.keys():
        rule = tran[key]
        newrule = ""
        for char in rule:
            replacement = char
            if char in RULE_CHARS and char not in available_chars:
                replacement = available_chars[RULE_CHARS.index(char) % len(available_chars)] #maps rule chars to available chars based on their index mod num_of_chars
            newrule += replacement
        newtran[key] = newrule

    return newtran

def plant_from_file(fname):
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

def produce_test_rand_plant():
    user_input = input("Put something: ")
    hasher = hashlib.sha256()
    hasher.update(user_input.encode('utf-8'))

    digest = hasher.digest()

    empty_stack_transitions_6op = {
         "."    :   "ABCDEFGAB[CD@" + STOP_CHAR + "FG"
        ,"A"    :   "ABCDEFG+-[+-@" + STOP_CHAR + "+-"
        ,"B"    :   "ABCDEFG+-[+-@" + STOP_CHAR + "[-"
        ,"C"    :   "ABCDEFG+-[+-@" + STOP_CHAR + "+-"
        ,"D"    :   "ABCDEFG+-[+-@" + STOP_CHAR + "[-"
        ,"E"    :   "ABCDEFG+-[+-@" + STOP_CHAR + "+-"
        ,"F"    :   "ABCDEFG+-[+-@" + STOP_CHAR + "[-"
        ,"G"    :   "ABCDEFG+-[+-@" + STOP_CHAR + "+-"
        ,"+"    :   "ABCDEFG+A[+D@" + STOP_CHAR + "+["
        ,"-"    :   "ABCDEFGB-[C-@" + STOP_CHAR + "[-"
        ,"]"    :   "ABCD[[[+-[+-@" + STOP_CHAR + "+-"
        ,"@"    :   "ABCDEFG+-[+-@" + STOP_CHAR + "+-"

    }

    nonempty_transitions_6op = {
         "A":"ABCDEFG+-[+-@" + STOP_CHAR + "]-"
        ,"B":"ABCDEFG+-[+-@" + STOP_CHAR + "+]"
        ,"C":"ABCDEFG+-[+-@" + STOP_CHAR + "[-"
        ,"D":"ABCDEFG+-[+-@" + STOP_CHAR + "+]"
        ,"E":"ABCDEFG+-[+-@" + STOP_CHAR + "[-"
        ,"F":"ABCDEFG+-[+-@" + STOP_CHAR + "+]"
        ,"G":"ABCDEFG+-[+-@" + STOP_CHAR + "]-"
        ,"+":"ABCDEFG+A[+D@" + STOP_CHAR + "+-]"
        ,"-":"ABCDEFGB-[C-@" + STOP_CHAR + "]-"
        ,"[":"+-+-EFG+-[+-@" + STOP_CHAR + "+-"
        ,"]":"ABCDEFG+-[+-@" + STOP_CHAR + "+-"
        ,"@":"ABCDEFG+-[+-@" + STOP_CHAR + "+-"
    }

    rules, seed, flower_color = pushdown_parser(digest, empty_stack_transitions_6op, nonempty_transitions_6op)

    print("Rules: \n" + str(rules))
    print("Seed: " + seed)
    print("Color: " + flower_color)
    
    return LSystem(rules, seed, 1, flower_color)

def main(scale, depth, win : t._Screen):
    test_mapping = {
         'X' : 'XX'
        ,'Y' : 'X[-Y][+Y]'
    }
    test_seed = 'Y'

    special_test_mapping = {
         'F' : 'XY[++G][--G][G]' 
        ,'G' : 'XX[++G@][--G@][G@]'
        ,'X' : 'XX'
        ,'Y' : 'YZ'
        ,'Z' : '[++++L][----L]X'
        ,'L' : 'MM[+++L][---L]L'
        ,'M' : 'MMM'
        ,'@' : ''
    }
    special_seed = 'F'


    l2 = produce_test_rand_plant()
    #l2 = LSystem(special_test_mapping, special_seed, 1)

    win.onkey(l2.reset_and_advance, "Return")
    win.onkey(speed_up, "Up")
    win.onkey(speed_down, "Down")
    win.onkey(zoom_in, "-")
    win.onkey(zoom_out, "+")
    

    t.left(90) #grow upwards
    win.screensize(3000, 2000)

    win.listen()
    win.mainloop()



if __name__ == '__main__':

    parser = argparse.ArgumentParser("Talk to the turtle and grow a procedurally-generated plant based on your input")
    parser.add_argument("--speed", "-s", help="Drawing speeed of the turtle. -1 for instant image generation", type=int, default=6)
    parser.add_argument("--scale", "-c", help="Custom scale factor for the drawing. Line length = default size/scale factor. Default 1", type=float, default=1)
    parser.add_argument("--depth", "-d", help="Jump to a depth immediately instead of showing each growth stage", type=int)

    args = parser.parse_args()

    try:
        win = t.Screen()
        win.title("PlantDreams")
        win.bgcolor(0.9, 0.83, 0.7) #TODO change these, theyre just copied from computerphile
        win.screensize(3000, 2000)
        t.color(0.3, 0.5, 0.2)

        if args.speed == -1:
            t.tracer(0, 0)
            t.speed("fastest")
        else:
            given_speed = min(10, max(0, args.speed))
            t.speed(given_speed)
    
        main(args.scale, args.depth, win)

    except t.Terminator:
        pass #Don't show error if user closes window prematurely
