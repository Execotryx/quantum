"""Controlled GF8 inverse with one held AND instead of three inverse bits.

Forward cost remains6T. HMR deletion pays one classically conditioned CCZ
(mean0.5T), saving two held qubits throughout the recursive inverse phase.
"""


def builder_class():
    from common import km
    from static_divisions import StaticArithmeticBuilder
    class OneMaskInverseBuilder(StaticArithmeticBuilder):
        def init_controlled_inverse(self,input,control,*,target='alloc'):
            if len(input)!=3:return super().init_controlled_inverse(input,control,target=target)
            b=self.native
            out=b.alloc_qubits(3) if isinstance(target,str) and target=='alloc' else target
            b.reset(out)
            held=b.alloc_qubits(1)
            b.init_and(control,input[0],held[0])
            b.init_and(control,input[1],out[2])
            b.cx(held[0],out[0]);b.cx(out[2],out[0])
            b.ccx(out[2],input[2],out[0])
            b.init_and(control,input[2],out[1])
            b.cx(out[1],out[0]);b.cx(out[1],out[2])
            b.ccx(held[0],input[1],out[1])
            b.ccx(held[0],input[2],out[2])
            return out,held

        def del_controlled_inverse(self,input,control,*,target,scaffold):
            if len(input)!=3:return super().del_controlled_inverse(input,control,target=target,scaffold=scaffold)
            assert len(scaffold)==1
            b=self.native;held=scaffold[0]
            measured=b.alloc_bits(3)
            b.hmr(target,measured)
            b.cz(measured[0],held)
            linear=b.alloc_bits(1)
            b.bit_store(linear[0],False)
            b.cx(measured[0],linear[0]);b.cx(measured[2],linear[0])
            b.ccz(linear[0],control,input[1])
            b.cx(measured[1],linear[0])
            b.ccz(linear[0],control,input[2])
            b.ccz(measured[1],held,input[1])
            b.ccz(measured[2],held,input[2])
            b.push_condition(measured[0])
            b.ccz(control,input[1],input[2])
            b.pop_condition()
            b.del_and(control,input[0],held)
            b.free(measured+linear)
    return OneMaskInverseBuilder
