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

#Let's cut out the multiply and divide instructions, since theyre kind of boring and probably won't lead to interesting phenomena
#We also make sure that after any non-letter operation, we disallow its negation. So - cant follow +, ] cant follow [, etc. This gets us down to 16 transitions for each
#state, except for the letters. TODO figure out the problem for the letters

#The 32 bytes: first 3 bits control the number of chars. The next 5 bits control the flower color. The remaining 62 nibbles are processed by the pushdown automata

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
   #	         Increment the line width by line width increment
   !	         Decrement the line width by line width increment
   @	         Draw a dot with line width radius
   &	         Swap the meaning of + and -
   (	         Decrement turning angle by turning angle increment
   )	         Increment turning angle by turning angle increment
"""

BASE_LENGTH = 10
BASE_ANGLE = 30
BASE_FLOWER_RAD = 2

ANGLE_INCREMENT = 0
WIDTH_INCREMENT = 0

given_speed = 6

class LSystem():
    def __init__(self, mapping : dict, seed : str, scale : float) -> None:
        self.mapping = mapping
        self.seed = seed
        self.state = seed
        self.scale = scale

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
        stack = []
        for char in self.state:
            if char == '+':
                t.left(BASE_ANGLE)
            elif char == '-':
                t.right(BASE_ANGLE)
            elif char == '[':
                #needs to save position and direction on the stack
                stack.append((t.heading(), t.pos()))
            elif char == ']':
                t.penup()
                head, pos = stack.pop() #If we add angle inc/dec, width inc/dec, flower color, or &, then we need to update the stack construction
                t.setheading(head)
                t.goto(pos)
                t.pendown()
            elif char == '@':
                t.color(1,1,1) #TODO change these colors, dont bother using floats
                t.begin_fill()
                t.circle(BASE_FLOWER_RAD)
                t.end_fill()
                t.color(0.3, 0.5, 0.2)
            else:
                t.forward(BASE_LENGTH/self.scale)

    def reset_and_advance(self):
        t.goto(0,0)
        t.clear() 
        t.setheading(90)
        self.get_next_state()
        self.draw_state()


def pushdown_parser_5op(digest):
    #Runs a pushdown automata for plants with only F, +, -, [, and ] operations (F is 2 to 7 different characters)
    pass


def pushdown_parser_full(digest):
    pass

def speed_up():
    t.speed("fastest")
    t.tracer(0,0)

def speed_down():
    t.tracer(1, 25)
    t.speed(given_speed)

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


    l1 = LSystem(test_mapping, test_seed, 1)
    l2 = LSystem(special_test_mapping, special_seed, 1)

    win.onkey(l2.reset_and_advance, "Return")
    win.onkey(speed_up, "Up")
    win.onkey(speed_down, "Down")
    

    t.left(90) #grow upwards
    win.screensize(3000, 2000) #TODO resize the screen to accomodate the size and scale of the graph. These are good dimensions for special_test with depth 5. Add more on each click

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
