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
   >	         Multiply the line length by the line length scale factor
   <	         Divide the line length by the line length scale factor
   &	         Swap the meaning of + and -
   (	         Decrement turning angle by turning angle increment
   )	         Increment turning angle by turning angle increment
"""

BASE_LENGTH = 10
BASE_ANGLE = 30

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
                head, pos = stack.pop()
                t.setheading(head)
                t.goto(pos)
                t.pendown()
            elif char == '@': #just draws a white dot for now
                pass
            else:
                t.forward(BASE_LENGTH/self.scale)


def main(scale, depth):
    test_mapping = {
         'X' : 'XX'
        ,'Y' : 'X[-Y][+Y]'
    }
    test_seed = 'Y'

    special_test_mapping = {
         'F' : 'XY[++G][--G][G]' #once @ is implemented, insert it after each of F and G
        ,'G' : 'XX[++G][--G][G]'
        ,'X' : 'XX'
        ,'Y' : 'YZ'
        ,'Z' : '[++++L][----L]X'
        ,'L' : 'MM[+++L][---L]L'
        ,'M' : 'MMM'
    }
    special_seed = 'F'

    t.left(90) #grow upwards

    l1 = LSystem(test_mapping, test_seed, 1)

    for i in range(5):
        print(l1.get_next_state())
        
        
    l1.draw_state() #TODO resize the screen to accomodate the size and scale of the graph
    t.exitonclick()


    #l2 = LSystem(special_test_mapping, special_seed)


if __name__ == '__main__':

    parser = argparse.ArgumentParser("Talk to the turtle and grow a procedurally-generated plant based on your input")
    parser.add_argument("--speed", "-s", help="Drawing speeed of the turtle. -1 for instant image generation", type=int, default=6)
    parser.add_argument("--scale", "-c", help="Custom scale factor for the drawing. Line length = default size/scale factor. Default 1", type=float, default=1)
    parser.add_argument("--depth", "-d", help="Jump to a depth immediately instead of showing each growth stage", type=int)

    args = parser.parse_args()

    if args.speed == -1:
        t.tracer(0, 0)
        t.speed("fastest")
    else:
        t.speed(t.speed(min(10, max(0, args.speed))))

    screen = t.Screen()
    screen.bgcolor(0.9, 0.83, 0.7) #TODO change these, theyre just copied from computerphile
    t.color(0.3, 0.5, 0.2)
    
    try:
        main(args.scale, args.depth)
    except t.Terminator:
        pass
