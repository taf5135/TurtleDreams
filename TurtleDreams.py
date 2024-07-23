import argparse
import hashlib
import turtle as t

import random
import time

SPECIAL_INPUTS = ["charlie", "caasi", "relic", "zem", "mara", "andy", "kyle", "miles", "sam", "tesoro"] #author added by popular demand
PROMPT_LIST = ["What's on your mind?", "What do you dream about?", "What was your first memory?", "Are you looking for something?", "Who are you?", "What's your question?"]

#cool pattern:
#"do you need m to explain it again?"

def square_spiral(size): 
    src = t.pos()
    size = int(size)

    parity = -1 * size % 2

    for _ in range(0, size % 12 + 3):
        t.fd(size)
        t.lt(parity * 90)
        size *= 0.8

    t.penup()
    t.setpos(src)
    t.pendown()
    return 0

def change_color(ins_color):
    #change the turtle color
    #get current color, shift left by 2, xor with input color
    curr_color = t.pencolor()
    ins_color = int(ins_color)
    
    new_color = []
    for color in curr_color:
        new_val = int(color) << 2
        new_val ^= ins_color
        new_val %= 255

        new_color.append(new_val)

    t.color(new_color)

def draw_recurse(inst_list, scale, depth):

    if depth < 0:
        return

    for inst in inst_list:
        if inst[0] == draw_recurse: #call the recursive part
            scaledown = inst[1][1] * scale
            pos = t.pos()
            draw_recurse(inst[1][0], scaledown, depth-1) 
            t.penup()
            t.setpos(pos) #saves the coords we came from and reloads them after the recursion
            t.pendown()
        else:
            operand = inst[1][0] / scale
            inst[0](operand) #call the function described with the value it's paired with, divided by scale factor

    return 0

def create_instructions(digest):
    inst = []

    #for each pair of bytes in digest
    #convert the first byte into an opcode -- one of fd, rt, lt, change_color, draw_recurse, square_spiral, or change_color
    #second byte is the argument. Usually this is just a value, but sometimes it needs two params, so we use a tuple

    for idx in range(0, len(digest), 2): 
        opcode = digest[idx]
        operand = digest[idx+1]

        inst_ops = [operand]
        if opcode < 70: 
            inst.append((t.fd, inst_ops)) 
        elif opcode < 100:
            inst.append((t.rt, inst_ops))
        elif opcode < 140:
            inst.append((t.lt, inst_ops))
        elif opcode < 155:
            inst.append((t.circle, inst_ops))
        elif opcode < 170:
            inst.append((square_spiral, inst_ops))
        elif opcode < 200:
            inst.append((change_color, inst_ops)) 
        else: #>=200
            inst_ops = [inst, operand % 4 + 1]
            inst.append((draw_recurse, inst_ops))

    return inst

def main():

    parser = argparse.ArgumentParser(description="Talk to the turtle and let them draw beautiful pictures for you")
    parser.add_argument("--speed", "-s", help="Drawing speeed of the turtle. -1 for instant image generation", type=int, default=6)
    parser.add_argument("--scale", "-c", help="Scale factor for the drawing. Line length = default size/scale factor. Default 1", type=int, default=1)
    parser.add_argument("--depth", "-d", help="Maximum recursion depth", type=int, default=5)
    parser.add_argument("--fishbowl", "-f", help="Fishbowl mode. On completion of a drawing, compute the next hash and start again", action="store_true")

    args = parser.parse_args()
    

    print(random.choice(PROMPT_LIST)) 
    user_input = input()

    if user_input.lower() in SPECIAL_INPUTS:
        print("I love you")


    hasher = hashlib.sha256()
    hasher.update(user_input.encode('utf-8'))

    digest = hasher.digest()

    #on initialize: set turtle color to the first 3 bytes of the hash
    firstrun = True
    while firstrun or args.fishbowl:
        firstrun = False

        t.colormode(255)
        t.color((digest[0], digest[1], digest[2]))
        if args.speed == -1:
            t.tracer(0, 0)
        else:
            t.speed(min(10, max(0, args.speed))) #enforce bounds

        inst = create_instructions(digest)
        draw_recurse(inst, args.scale, args.depth)
        
        t.update()
        time.sleep(5)

        next_seed = str(time.time()).encode('utf-8')
        hasher.update(next_seed)
        digest = hasher.digest()
        print(next_seed.decode('utf-8'))
        t.reset()
        
    t.exitonclick()

    return 0

if __name__ == "__main__":
    try:
        main()
    except t.Terminator:
        pass