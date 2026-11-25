// Copyright 2026 Syed Asad Ali. SPDX-License-Identifier: Apache-2.0
// Credits: Opus and Astra. Exact finite truth search, not quantum circuit code.
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <random>
#include <string>
#include <vector>
using u128=unsigned __int128;
u128 parse(std::string s){u128 x=0;for(char c:s){if(c=='x'||c=='X'){x=0;continue;}unsigned d=c>='a'?c-'a'+10:c>='A'?c-'A'+10:c-'0';x=(x<<4)|d;}return x;}
int top(u128 x){uint64_t hi=x>>64;return hi?127-__builtin_clzll(hi):63-__builtin_clzll((uint64_t)x);}
bool insert(std::array<u128,128>& b,u128 x){while(x){int p=top(x);if(!b[p]){b[p]=x;return true;}x^=b[p];}return false;}
u128 parity(uint64_t m,const std::vector<u128>& f){u128 v=0;while(m){int i=__builtin_ctzll(m);m&=m-1;v^=f[i];}return v;}
int main(){
 int n,r,k;uint64_t trials,seed;double seconds;
 if(!(std::cin>>n>>r>>k>>trials>>seed>>seconds)||n>62||r>30)return 2;
 std::vector<u128> f(n),t(r);std::string s;for(auto&v:f){std::cin>>s;v=parse(s);}for(auto&v:t){std::cin>>s;v=parse(s);}
 std::array<u128,128> base{};insert(base,~u128(0));for(auto v:f)insert(base,v);
 std::mt19937_64 rng(seed);uint64_t mask=(uint64_t(1)<<n)-1;auto began=std::chrono::steady_clock::now();
 for(uint64_t trial=0;trial<trials;trial++){
  if((trial&1023)==0&&std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count()>seconds){std::cout<<"TIME_LIMIT "<<trial<<"\n";return 0;}
  auto basis=base;std::vector<uint64_t> factors;
  for(int j=0;j<k;j++){
   uint64_t m=rng()&mask;if(!m)m=1;factors.push_back(m);u128 left=parity(m,f);
   for(auto v:f)insert(basis,left&v);
  }
  std::array<uint32_t,128> tc{};
  for(int j=0;j<r;j++){
   u128 v=t[j];uint32_t c=uint32_t(1)<<j;
   while(v){int p=top(v);if(!basis[p]){basis[p]=v;tc[p]=c;break;}v^=basis[p];c^=tc[p];}
   if(!v&&c){std::cout<<"FOUND "<<trial+1<<" "<<c;for(auto m:factors)std::cout<<" "<<m;std::cout<<"\n";return 0;}
  }
 }
 std::cout<<"BOUNDED_NONE "<<trials<<"\n";
}
