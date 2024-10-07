import sys

from crossword import *
from collections import deque


class CrosswordCreator():

    count = 0

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for variable, possible_words in self.domains.items():
            possible_words_consistency = set()
            for word in possible_words:
                if len(word) == variable.length:
                    possible_words_consistency.add(word)
            self.domains[variable] = possible_words_consistency

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        intersection = self.get_index_overlap(x, y)
        if intersection is None:
            return False
        x_possible_words = self.domains[x]
        y_possible_words = self.domains[y]
        x_possible_words_consistency = set()
        revised = False

        # For each word in x domain's check if there is an option to Y
        for x_word in x_possible_words:
            arc_consistency = False
            for y_word in y_possible_words:
                if len(x_word) > intersection[0] and len(y_word) > intersection[1]:
                    if x_word[intersection[0]] == y_word[intersection[1]]:
                        arc_consistency = True  
                        break
            if arc_consistency == True or intersection is None:
                x_possible_words_consistency.add(x_word)

        # If we exclude some value return True
        if len(x_possible_words_consistency) < len(x_possible_words):
            self.domains[x] = x_possible_words_consistency
            revised = True
        
        return revised

    #This function return a tuple with the index intersection between these two variables
    def get_index_overlap(self, x, y):
        intersection = self.crossword.overlaps.get((x, y))
        if intersection is not None:
            return intersection
        return None
        
    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
        # Create the initial queue of arcs (all overlaps)
            queue = deque([arc for arc in self.crossword.overlaps if self.crossword.overlaps[arc] is not None])
        else:
            queue = deque(arcs)

        while queue:
            x, y = queue.popleft()
            
            # If revision is made, we need to check neighbors of x
            if self.revise(x, y):
                # If domain of x is empty, return False
                if len(self.domains[x]) == 0:
                    return False
                
                # Add neighbors of x, except for y, back to the queue
                for neighbor in self.get_neighbors(x):
                    if neighbor != y:
                        queue.append((neighbor, x))
        return True

    #Iterate over the edges and return a list of variables that intersect with X except Y         
    def get_neighbors(self, x):
        overlaps = self.crossword.overlaps
        neighbors = list()
        for variables, intersection in overlaps.items():
            if x == variables[0] and intersection is not None:
                neighbors.append(variables[1])
        return neighbors

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for variable in self.crossword.variables:
            if variable not in assignment or assignment[variable] is None:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Check the length, check if they are distinct and call ac3
        for variable, value in assignment.items():
            if value is not None:
                if variable.length != len(value):
                    return False
                
        # Check if they are distinct
        distinct = self.are_values_distinct(assignment)
        if distinct == False:
            return False

        # Check if they are arc consistency
        for variables, overlap in self.crossword.overlaps.items():
            if overlap is not None and variables[0] in assignment and variables[1] in assignment:
                word_a = assignment[variables[0]]
                word_b = assignment[variables[1]]
                if word_a is not None and word_b is not None:
                    if word_a[overlap[0]] != word_b[overlap[1]]:
                        return False
            
        return True

    def are_values_distinct(self, d):
        values = [v for v in d.values() if v is not None]
        return len(values) == len(set(values))

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        # Get the neighbors of the variable
        neighbors = self.get_neighbors(var)
        var_domain = self.domains[var]
        
        # Dictionary to keep track of the number of ruled-out values for each domain value
        word_dict = {value: 0 for value in var_domain}

        # Iterate over each value in the domain of `var`
        for value in var_domain:
            # Check each neighbor of `var`
            for neighbor in neighbors:
                # Only consider neighbors that are not yet assigned in the current assignment
                if neighbor not in assignment:
                    # Get the intersection between `var` and `neighbor`
                    intersection = self.get_index_overlap(var, neighbor)
                    
                    # Only proceed if there is an intersection
                    if intersection is not None:
                        # Iterate over the domain of the neighbor
                        for neighbor_value in self.domains[neighbor]:
                            # Check if the value for `var` is incompatible with `neighbor_value`
                            if value[intersection[0]] != neighbor_value[intersection[1]]:
                                word_dict[value] += 1  # This value rules out one possibility for the neighbor

        # Sort the domain values by the number of ruled-out values (ascending order)
        sorted_values = sorted(word_dict, key=word_dict.get)
        
        return sorted_values
            

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # Initialize to store variables with MRV
        unassigned_variables = []
        
        for variable in self.crossword.variables:
            if variable not in assignment or assignment[variable] is None:
                remaining_values = len(self.domains[variable])
                unassigned_variables.append((variable, remaining_values))

        # Sort by MRV (minimum remaining values), then by degree (maximum neighbors)
        unassigned_variables.sort(
            key=lambda x: (x[1], -len(self.get_neighbors(x[0])))
        )

        # Return the variable with the smallest remaining values and highest degree in case of a tie
        return unassigned_variables[0][0] if unassigned_variables else None

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if len(assignment) == 0:
            for var in self.domains.keys():
                assignment[var] = None

        if self.assignment_complete(assignment):
            return assignment
        
        var = self.select_unassigned_variable(assignment)

        for value in self.order_domain_values(var, assignment):
            assignment_copy = assignment.copy()
            assignment_copy[var] = value 

            if self.consistent(assignment_copy):
                result = self.backtrack(assignment_copy)
                if result is not None:
                    return result

        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()

