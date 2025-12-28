from lucas import function
from lucas.actorc.actor import ActorFunction

@function(
    wrapper=ActorFunction,
    dependency=[],
    provider="actor",
    name="unikernel_func",
    backend="unikernel"
)
def unikernel_func(a:int,b: int):
    """
    let add value =
    let open Yojson.Basic.Util intry
    let a = value D member "a"D to_int_option in
    let b = value D member "b"D to_int_option in
    match a, b with
    | Some a,Some b Ok (`Int(a +b))
    |-,-  Error "function is not valid"with Type_error (msg,-)  Error ("input type error")
    let handlers = [
        "add",add;
    ]
    """
    