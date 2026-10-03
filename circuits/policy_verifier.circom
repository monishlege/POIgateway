pragma circom 2.1.6;

include "circomlib/circuits/poseidon.circom";

template PolicyVerifier() {
    signal input currentStateHash;
    signal input nextStateHash;
    signal input actionId;
    signal input salt;

    component transitionHash = Poseidon(3);
    transitionHash.inputs[0] <== currentStateHash;
    transitionHash.inputs[1] <== actionId;
    transitionHash.inputs[2] <== salt;

    transitionHash.out === nextStateHash;
}

component main {public [currentStateHash, nextStateHash]} = PolicyVerifier();