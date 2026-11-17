% hanoi.pl -- Tower of Hanoi solver (SWI-Prolog)
% Usage: swipl -q hanoi.pl 4
:- initialization(main, main).

%! hanoi(+N, +From, +To, +Via, -Moves) is det.
% Difference lists keep this O(2^N) instead of O(N * 2^N) from append/3.
hanoi(N, From, To, Via, Moves) :-
    must_be(nonneg, N),
    phrase(solve(N, From, To, Via), Moves).

solve(0, _, _, _) --> !, [].
solve(N, From, To, Via) -->
    { N1 is N - 1 },
    solve(N1, From, Via, To),
    [move(N, From, To)],
    solve(N1, Via, To, From).

% Rule-checking predicate (independent oracle for the solver).
valid_move(State0, move(D, F, T), State) :-
    get_assoc(F, State0, [D|RestF]),
    get_assoc(T, State0, DestT),
    ( DestT = [] ; DestT = [Top|_], D < Top ), !,
    put_assoc(F, State0, RestF, S1),
    put_assoc(T, S1, [D|DestT], State).

% ---- Hint engine: optimal next move from ANY legal position ----------
% Pegs is a list: the peg of disk 1, disk 2, ... N.  Goal: all on `right`.
other(A, B, C) :- member(C, [left, middle, right]), C \== A, C \== B, !.

all_on(0, _, _) :- !.
all_on(K, P, Pegs) :- nth1(K, Pegs, P), K1 is K - 1, all_on(K1, P, Pegs).

best_move(K, Target, Pegs, Move) :-
    K > 0,
    nth1(K, Pegs, L),
    K1 is K - 1,
    (   L == Target
    ->  best_move(K1, Target, Pegs, Move)
    ;   other(L, Target, O),
        (   all_on(K1, O, Pegs)
        ->  Move = move(K, L, Target)
        ;   best_move(K1, O, Pegs, Move)
        )
    ).

main([hint, NAtom|Pegs]) :-
    atom_number(NAtom, N), length(Pegs, N),
    (   best_move(N, right, Pegs, move(D, F, T))
    ->  format("~d ~w ~w~n", [D, F, T])
    ;   format("done~n")
    ).
main([NAtom]) :-
    atom_number(NAtom, N),
    hanoi(N, left, right, middle, Moves),
    forall(member(move(D, F, T), Moves), format("~d ~w ~w~n", [D, F, T])).
main(_) :-
    format(user_error, "usage: swipl hanoi.pl <disks>~n", []), halt(1).
