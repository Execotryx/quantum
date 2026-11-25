// Copyright 2026 Syed Asad Ali. Apache-2.0. Credits: Opus and Astra.
// Independent MinRank kernel attack, resumable at validated triple boundaries.
// Input: 75 by 15 little-endian uint64 values, each an output35-bit vector.
// Choose two low duals x,y, enumerate their small high-kernel, and find a
// third independent low dual z. Five disjoint triples give a full low basis.
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using U = unsigned __int128;
using Row = std::array<uint64_t,15>;
int top(U x) { uint64_t h=x>>64; return h ? 127-__builtin_clzll(h) : 63-__builtin_clzll((uint64_t)x); }
int rank15(const std::vector<uint16_t>& rows) {
    uint16_t piv[15]={}; int rank=0;
    for (auto x:rows) while(x) {
        int p=31-__builtin_clz((unsigned)x);
        if(piv[p]) x^=piv[p]; else {piv[p]=x;rank++;break;}
    }
    return rank;
}
std::vector<U> kernel75(const uint64_t* x,const uint64_t* y) {
    U p[70]={},co[70]={};std::vector<U> out;
    for(int h=0;h<75;h++) {
        U v=U(x[h])|(U(y[h])<<35), c=U(1)<<h;
        while(v) {int b=top(v);if(p[b]) {v^=p[b];c^=co[b];}else{p[b]=v;co[b]=c;break;}}
        if(!v)out.push_back(c);
    }
    return out;
}
uint16_t third(const Row& M, int px,int py) {
    uint64_t piv[35]={};uint16_t co[35]={};
    for(int m=0;m<15;m++) if(m!=px && m!=py) {
        uint64_t v=M[m];uint16_t c=uint16_t(1)<<m;
        while(v){int b=63-__builtin_clzll(v);if(piv[b]){v^=piv[b];c^=co[b];}else{piv[b]=v;co[b]=c;break;}}
        if(!v)return c;
    }
    return 0;
}
int main(int argc,char** argv) {
    if(argc<3){std::cerr<<"input.bin seed [seconds] [allowed_low_mask] [min_planes] [resume_rows.txt]\n";return 2;}
    Row T[75];std::ifstream f(argv[1],std::ios::binary);
    f.read(reinterpret_cast<char*>(T),sizeof(T));if(!f){std::cerr<<"bad input size\n";return 2;}
    auto seed=std::stoull(argv[2]);double seconds=argc>3?std::stod(argv[3]):300;
    uint16_t allowed=argc>4?std::stoi(argv[4]):32767;
    int min_planes=argc>5?std::stoi(argv[5]):0;
    std::mt19937_64 rng(seed);
    std::vector<uint64_t> cache(32768*75);
    for(int v=1;v<32768;v++) {
        int b=__builtin_ctz((unsigned)v), w=v^(1<<b);
        for(int h=0;h<75;h++)cache[v*75+h]=cache[w*75+h]^T[h][b];
    }
    std::vector<uint16_t> rows;
    if(argc>6) {
        std::ifstream prior(argv[6]); unsigned value;
        if(!prior) return 2;
        while(prior>>value) {
            if(value>32767) return 2;
            rows.push_back(uint16_t(value));
        }
    }
    if(rows.size()%3 || rows.size()>15 || rank15(rows)!=int(rows.size())) return 2;
    auto start=std::chrono::steady_clock::now();
    uint64_t count=0,matrices=0;
    for(int block=int(rows.size()/3);block<5;block++) {
        bool found=false;
        for(uint64_t it=0;!found;it++) {
            if((it&4095)==0 && std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()>seconds){
                std::cout<<"{\"status\":\"TIME_LIMIT\",\"blocks\":"<<block<<",\"queries\":"<<count<<",\"matrices\":"<<matrices<<"}\n";return 3;
            }
            uint16_t x=rng()&allowed,y=rng()&allowed;
            if(!x||!y||x==y)continue;
            auto test=rows;test.push_back(x);test.push_back(y);
            if(rank15(test)!=int(rows.size())+2)continue;
            int px=__builtin_ctz((unsigned)x);
            uint16_t yy=y^((y>>px&1)?x:0);int py=__builtin_ctz((unsigned)yy);
            auto A=kernel75(&cache[x*75],&cache[y*75]);count++;
            if(A.empty())continue;
            if(A.size()>12) A.resize(12); // explicit bounded enumeration
            std::vector<Row> P(A.size());
            for(size_t i=0;i<A.size();i++)for(int h=0;h<75;h++)if((A[i]>>h)&1)
                for(int m=0;m<15;m++)P[i][m]^=T[h][m];
            Row M={};
            for(unsigned s=1;s<(1u<<A.size());s++) {
                int b=__builtin_ctz(s);
                for(int m=0;m<15;m++)M[m]^=P[b][m];
                matrices++;auto z=third(M,px,py);
                if(!z || (z&~allowed))continue;
                test.push_back(z);
                if(rank15(test)==int(rows.size())+3) {
                    if(min_planes) {
                        uint16_t aa[7]={x,x,y,x,y,z,uint16_t(x^y)};
                        uint16_t bb[7]={y,z,z,uint16_t(y^z),uint16_t(x^z),uint16_t(x^y),uint16_t(x^z)};
                        int np=0;
                        for(int j=0;j<7;j++) if(kernel75(&cache[aa[j]*75],&cache[bb[j]*75]).size()>=6) np++;
                        if(np<min_planes){test.pop_back();continue;}
                    }
                    rows.push_back(x);rows.push_back(y);rows.push_back(z);found=true;
                    std::cout<<"{\"event\":\"block\",\"block\":"<<block<<",\"seed\":"<<seed
                        <<",\"queries\":"<<count<<",\"matrices\":"<<matrices<<",\"triple\":["<<x<<","<<y<<","<<z
                        <<"],\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n"<<std::flush;
                    break;
                }
                test.pop_back();
            }
        }
    }
    std::cout<<"{\"status\":\"FOUND\",\"seed\":"<<seed<<",\"rows\":[";
    for(size_t i=0;i<rows.size();i++)std::cout<<(i?",":"")<<rows[i];
    std::cout<<"],\"queries\":"<<count<<",\"matrices\":"<<matrices<<"}\n";
}
